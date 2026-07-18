"""Editorial backup scope, retention, and integrity verification (US-036).

Defines package contracts under metadata/backups/, verifies integrity with
pass/fail/blocked outcomes, and optionally creates/prunes packages. Does not
restore source editorial trees (US-037). No FastAPI routes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from silverman_blog_linkedin.file_reader import normalize_relative_path

MANIFEST_SCHEMA_VERSION = "1"
MANIFEST_FILENAME = "manifest.json"
CONTENT_DIRNAME = "content"
BACKUPS_RELATIVE = "metadata/backups"
DEFAULT_RETENTION_KEEP_COUNT = 7

IntegrityStatus = Literal["pass", "fail", "blocked"]

# --- Reason codes ---

REASON_PACKAGE_MISSING = "backup_package_missing"
REASON_MANIFEST_UNREADABLE = "backup_manifest_unreadable"
REASON_MANIFEST_SCHEMA_AMBIGUOUS = "backup_manifest_schema_ambiguous"
REASON_HASH_MISMATCH = "backup_hash_mismatch"
REASON_SIZE_MISMATCH = "backup_size_mismatch"
REASON_FILE_MISSING = "backup_file_missing"
REASON_PATH_UNSAFE = "backup_path_unsafe"
REASON_EXCLUDED_CONTENT = "backup_excluded_content_present"
REASON_SCOPE_CLASS_MISSING = "backup_scope_class_missing"
REASON_SCOPE_AMBIGUOUS = "backup_scope_ambiguous_excluded"

# Included scope path classes (directory prefixes without trailing slash for
# empty-class representation; files under class/ are in scope).
INCLUDED_SCOPE_CLASSES: tuple[str, ...] = (
    "blog-posts/ready",
    "blog-posts/queued",
    "blog-posts/processed",
    "blog-posts/error",
    "linkedin-posts/review",
    "linkedin-posts/approved",
    "linkedin-posts/published",
    "metadata/campaigns",
    "metadata/runs",
    "editorial-calendar",
    "prompts",
)

_SECRET_BASENAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "credentials.json",
        "credentials.yaml",
        "credentials.yml",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        "linkedin_token.json",
        "token.json",
    }
)
_SECRET_NAME_FRAGMENTS = (
    ".env",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "client_secret",
)
_JUNK_BASENAMES = frozenset({".DS_Store", "Thumbs.db"})
_JUNK_DIRNAMES = frozenset({"__pycache__", ".git"})
_JUNK_SUFFIXES = (".tmp", ".swp", "~")


@dataclass
class IntegrityResult:
    status: IntegrityStatus
    reason_codes: list[str] = field(default_factory=list)
    backup_id: str | None = None
    files_checked: int = 0
    mismatch_count: int = 0
    relative_paths_noted: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "backup_id": self.backup_id,
            "files_checked": self.files_checked,
            "mismatch_count": self.mismatch_count,
            "relative_paths_noted": list(self.relative_paths_noted),
            "summary": self.summary,
        }


def backups_root(base_path: Path) -> Path:
    return Path(base_path).resolve() / BACKUPS_RELATIVE


def package_dir(base_path: Path, backup_id: str) -> Path:
    return backups_root(base_path) / backup_id


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def make_backup_id(now: datetime | None = None) -> str:
    stamp = (now or _utc_now()).strftime("%Y%m%dT%H%M%SZ")
    short = uuid.uuid4().hex[:6]
    return f"editorial-backup-{stamp}-{short}"


def is_path_safe_relative(relative_path: str) -> bool:
    """Return True when path is relative, has no '..', and is not absolute."""
    normalized = normalize_relative_path(relative_path)
    if not normalized:
        return False
    if normalized.startswith("/") or normalized.startswith("\\"):
        return False
    if PurePosixPath(normalized).is_absolute():
        return False
    # Drive-letter absolute (Windows-style) in string form
    if len(normalized) >= 2 and normalized[1] == ":" and normalized[0].isalpha():
        return False
    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        return False
    return True


def is_excluded_relative_path(relative_path: str) -> bool:
    """True when path must not appear in a backup package content tree."""
    normalized = normalize_relative_path(relative_path)
    if not normalized:
        return True
    posix = PurePosixPath(normalized)
    parts = posix.parts

    # Nested backup packages
    if "metadata" in parts:
        try:
            idx = parts.index("metadata")
            if idx + 1 < len(parts) and parts[idx + 1] == "backups":
                return True
        except ValueError:
            pass

    name = posix.name
    if name in _SECRET_BASENAMES or name in _JUNK_BASENAMES:
        return True
    if any(part in _JUNK_DIRNAMES for part in parts):
        return True
    lower_name = name.lower()
    for fragment in _SECRET_NAME_FRAGMENTS:
        if fragment in lower_name:
            return True
    if any(lower_name.endswith(suffix) for suffix in _JUNK_SUFFIXES):
        return True
    return False


def path_in_included_scope(relative_path: str) -> bool:
    normalized = normalize_relative_path(relative_path)
    if not normalized or not is_path_safe_relative(normalized):
        return False
    if is_excluded_relative_path(normalized):
        return False
    for scope_class in INCLUDED_SCOPE_CLASSES:
        if normalized == scope_class or normalized.startswith(scope_class + "/"):
            return True
    return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _scope_class_for_path(relative_path: str) -> str | None:
    normalized = normalize_relative_path(relative_path)
    for scope_class in INCLUDED_SCOPE_CLASSES:
        if normalized == scope_class or normalized.startswith(scope_class + "/"):
            return scope_class
    return None


def _build_scope_declaration(file_relpaths: list[str]) -> dict[str, Any]:
    represented: set[str] = set()
    for rel in file_relpaths:
        scope_class = _scope_class_for_path(rel)
        if scope_class:
            represented.add(scope_class)
    empty = {
        scope_class: "no_files_present"
        for scope_class in INCLUDED_SCOPE_CLASSES
        if scope_class not in represented
    }
    return {
        "included_classes": list(INCLUDED_SCOPE_CLASSES),
        "empty_classes": empty,
    }


def iter_source_files(base_path: Path) -> list[tuple[str, Path]]:
    """List (relative_path, absolute_path) for included editorial files."""
    root = Path(base_path).resolve()
    found: list[tuple[str, Path]] = []
    for scope_class in INCLUDED_SCOPE_CLASSES:
        class_dir = root / scope_class
        if not class_dir.is_dir():
            continue
        for path in sorted(class_dir.rglob("*")):
            if not path.is_file():
                continue
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if not path_in_included_scope(relative):
                continue
            found.append((relative, path))
    return found


def create_editorial_backup(
    base_path: Path,
    *,
    backup_id: str | None = None,
    keep_count: int = DEFAULT_RETENTION_KEEP_COUNT,
) -> dict[str, Any]:
    """Copy included scope into metadata/backups/<backup_id>/ only.

    Does not modify source editorial trees. Excludes excluded classes.
    """
    root = Path(base_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"editorial base path not found: {root}")

    bid = backup_id or make_backup_id()
    if not is_path_safe_relative(bid) or "/" in bid or "\\" in bid:
        raise ValueError("backup_id must be a single safe path segment")

    pkg = package_dir(root, bid)
    content_root = pkg / CONTENT_DIRNAME
    if pkg.exists():
        raise FileExistsError(f"backup package already exists: {bid}")

    backups_root(root).mkdir(parents=True, exist_ok=True)
    content_root.mkdir(parents=True, exist_ok=False)

    file_index: list[dict[str, Any]] = []
    source_files = iter_source_files(root)
    for relative, src in source_files:
        dest = content_root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        size = dest.stat().st_size
        digest = _sha256_file(dest)
        file_index.append(
            {
                "path": relative,
                "sha256": digest,
                "size_bytes": size,
            }
        )

    scope = _build_scope_declaration([entry["path"] for entry in file_index])
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "backup_id": bid,
        "created_at_utc": _utc_now_iso(),
        "scope": scope,
        "retention": {"keep_count": keep_count},
        "files": file_index,
    }
    manifest_path = pkg / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "backup_id": bid,
        "package_relative": f"{BACKUPS_RELATIVE}/{bid}",
        "files_copied": len(file_index),
        "created_at_utc": manifest["created_at_utc"],
    }


def _load_manifest(manifest_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Return (manifest, blocked_reason_code)."""
    if not manifest_path.is_file():
        return None, REASON_MANIFEST_UNREADABLE
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, REASON_MANIFEST_UNREADABLE
    if not isinstance(data, dict):
        return None, REASON_MANIFEST_SCHEMA_AMBIGUOUS
    schema = data.get("schema_version")
    if schema != MANIFEST_SCHEMA_VERSION:
        return None, REASON_MANIFEST_SCHEMA_AMBIGUOUS
    if not isinstance(data.get("backup_id"), str) or not data["backup_id"]:
        return None, REASON_MANIFEST_SCHEMA_AMBIGUOUS
    if not isinstance(data.get("files"), list):
        return None, REASON_MANIFEST_SCHEMA_AMBIGUOUS
    if not isinstance(data.get("scope"), dict):
        return None, REASON_MANIFEST_SCHEMA_AMBIGUOUS
    return data, None


def verify_editorial_backup(
    base_path: Path,
    backup_id: str,
) -> IntegrityResult:
    """Verify a backup package. Read-only; does not restore source trees."""
    root = Path(base_path).resolve()
    bid = normalize_relative_path(backup_id)
    if not bid or "/" in bid or "\\" in bid or not is_path_safe_relative(bid):
        return IntegrityResult(
            status="blocked",
            reason_codes=[REASON_PACKAGE_MISSING],
            backup_id=None,
            summary="Backup id is missing or path-unsafe; verification blocked.",
        )

    pkg = package_dir(root, bid)
    if not pkg.is_dir():
        return IntegrityResult(
            status="blocked",
            reason_codes=[REASON_PACKAGE_MISSING],
            backup_id=bid,
            summary="Backup package directory is missing; verification blocked.",
        )

    manifest, blocked = _load_manifest(pkg / MANIFEST_FILENAME)
    if blocked or manifest is None:
        return IntegrityResult(
            status="blocked",
            reason_codes=[blocked or REASON_MANIFEST_UNREADABLE],
            backup_id=bid,
            summary="Manifest is missing, unreadable, or schema-ambiguous.",
        )

    reason_codes: list[str] = []
    noted: list[str] = []
    files_checked = 0
    mismatch_count = 0
    content_root = pkg / CONTENT_DIRNAME
    represented: set[str] = set()

    # Scope declaration must list included classes (fail closed on ambiguity).
    scope = manifest["scope"]
    declared_classes = scope.get("included_classes")
    if not isinstance(declared_classes, list):
        return IntegrityResult(
            status="blocked",
            reason_codes=[REASON_MANIFEST_SCHEMA_AMBIGUOUS],
            backup_id=bid,
            summary="Manifest scope.included_classes is ambiguous.",
        )
    empty_classes = scope.get("empty_classes")
    if empty_classes is not None and not isinstance(empty_classes, dict):
        return IntegrityResult(
            status="blocked",
            reason_codes=[REASON_MANIFEST_SCHEMA_AMBIGUOUS],
            backup_id=bid,
            summary="Manifest scope.empty_classes is ambiguous.",
        )

    for entry in manifest["files"]:
        if not isinstance(entry, dict):
            reason_codes.append(REASON_MANIFEST_SCHEMA_AMBIGUOUS)
            continue
        rel = entry.get("path")
        if not isinstance(rel, str):
            reason_codes.append(REASON_MANIFEST_SCHEMA_AMBIGUOUS)
            continue
        rel_norm = normalize_relative_path(rel)
        if not is_path_safe_relative(rel_norm):
            if REASON_PATH_UNSAFE not in reason_codes:
                reason_codes.append(REASON_PATH_UNSAFE)
            noted.append(rel_norm if is_path_safe_relative(rel_norm) else "(unsafe)")
            # Do not follow unsafe paths
            continue
        if is_excluded_relative_path(rel_norm):
            if REASON_EXCLUDED_CONTENT not in reason_codes:
                reason_codes.append(REASON_EXCLUDED_CONTENT)
            noted.append(rel_norm)
            continue

        scope_class = _scope_class_for_path(rel_norm)
        if scope_class:
            represented.add(scope_class)

        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if not isinstance(expected_hash, str) or not isinstance(expected_size, int):
            reason_codes.append(REASON_MANIFEST_SCHEMA_AMBIGUOUS)
            continue

        # Resolve under content root only; reject escape via resolve check.
        candidate = (content_root / rel_norm).resolve()
        try:
            candidate.relative_to(content_root.resolve())
        except ValueError:
            if REASON_PATH_UNSAFE not in reason_codes:
                reason_codes.append(REASON_PATH_UNSAFE)
            noted.append(rel_norm)
            continue

        if not candidate.is_file():
            if REASON_FILE_MISSING not in reason_codes:
                reason_codes.append(REASON_FILE_MISSING)
            noted.append(rel_norm)
            mismatch_count += 1
            continue

        files_checked += 1
        actual_size = candidate.stat().st_size
        if actual_size != expected_size:
            if REASON_SIZE_MISMATCH not in reason_codes:
                reason_codes.append(REASON_SIZE_MISMATCH)
            noted.append(rel_norm)
            mismatch_count += 1
            continue
        actual_hash = _sha256_file(candidate)
        if actual_hash != expected_hash:
            if REASON_HASH_MISMATCH not in reason_codes:
                reason_codes.append(REASON_HASH_MISMATCH)
            noted.append(rel_norm)
            mismatch_count += 1
            continue

        # Successful entry already counted in represented above.

    # Scan content tree for excluded paths not necessarily listed in manifest.
    if content_root.is_dir():
        for path in content_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(content_root).as_posix()
            except ValueError:
                continue
            if is_excluded_relative_path(rel):
                if REASON_EXCLUDED_CONTENT not in reason_codes:
                    reason_codes.append(REASON_EXCLUDED_CONTENT)
                if rel not in noted:
                    noted.append(rel)

    # Required scope classes must be represented or explicitly empty.
    empty_map = empty_classes if isinstance(empty_classes, dict) else {}
    for scope_class in INCLUDED_SCOPE_CLASSES:
        if scope_class in represented:
            continue
        if scope_class in empty_map:
            continue
        # Also accept declaration that class is in included list but missing
        # from empty_classes only when no files expected — fail closed.
        if REASON_SCOPE_CLASS_MISSING not in reason_codes:
            reason_codes.append(REASON_SCOPE_CLASS_MISSING)
        noted.append(scope_class)

    # Deduplicate reason codes preserving order
    seen: set[str] = set()
    ordered_reasons: list[str] = []
    for code in reason_codes:
        if code not in seen:
            seen.add(code)
            ordered_reasons.append(code)

    # Cap noted paths for secret-safe brevity (relative only, no bodies)
    noted_unique: list[str] = []
    for item in noted:
        if item not in noted_unique and is_path_safe_relative(item):
            noted_unique.append(item)
        if len(noted_unique) >= 20:
            break

    if ordered_reasons:
        # Schema ambiguity after readable parse still blocks completion when
        # structural fields were wrong mid-stream; treat as fail if we got past
        # initial load unless only ambiguous entries.
        if (
            REASON_MANIFEST_SCHEMA_AMBIGUOUS in ordered_reasons
            and len(ordered_reasons) == 1
            and files_checked == 0
            and mismatch_count == 0
        ):
            status: IntegrityStatus = "blocked"
            summary = "Manifest schema is ambiguous; verification blocked."
        else:
            status = "fail"
            summary = (
                "Backup integrity failed: "
                + ", ".join(ordered_reasons)
            )
        return IntegrityResult(
            status=status,
            reason_codes=ordered_reasons,
            backup_id=bid,
            files_checked=files_checked,
            mismatch_count=mismatch_count,
            relative_paths_noted=noted_unique,
            summary=summary,
        )

    return IntegrityResult(
        status="pass",
        reason_codes=[],
        backup_id=bid,
        files_checked=files_checked,
        mismatch_count=0,
        relative_paths_noted=[],
        summary="Backup integrity verification passed.",
    )


def list_backup_ids(base_path: Path) -> list[str]:
    root = backups_root(base_path)
    if not root.is_dir():
        return []
    ids = [
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ]
    return sorted(ids)


def prune_editorial_backups(
    base_path: Path,
    *,
    keep_count: int = DEFAULT_RETENTION_KEEP_COUNT,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove older integrity-pass packages under metadata/backups/ only.

    Never deletes fail/blocked packages. Never touches source editorial trees.
    """
    if keep_count < 1:
        raise ValueError("keep_count must be >= 1")

    root = Path(base_path).resolve()
    backups = backups_root(root)
    # Defense: only operate under backups root
    backups_resolved = backups.resolve()
    if not backups_resolved.is_dir():
        return {
            "kept": [],
            "deleted": [],
            "retained_failed_or_blocked": [],
            "dry_run": dry_run,
            "keep_count": keep_count,
        }

    passing: list[str] = []
    retained_failed: list[str] = []
    for bid in list_backup_ids(root):
        result = verify_editorial_backup(root, bid)
        if result.status == "pass":
            passing.append(bid)
        else:
            retained_failed.append(bid)

    # Newest first: backup_id is UTC-sortable by construction; also sort reverse
    passing_sorted = sorted(passing, reverse=True)
    keep = passing_sorted[:keep_count]
    prune_candidates = passing_sorted[keep_count:]

    deleted: list[str] = []
    for bid in prune_candidates:
        pkg = package_dir(root, bid).resolve()
        try:
            pkg.relative_to(backups_resolved)
        except ValueError:
            continue
        if not pkg.is_dir():
            continue
        if not dry_run:
            shutil.rmtree(pkg)
        deleted.append(bid)

    return {
        "kept": keep,
        "deleted": deleted,
        "retained_failed_or_blocked": retained_failed,
        "dry_run": dry_run,
        "keep_count": keep_count,
    }


def refuse_excluded_scope_expansion(requested_relative: str) -> IntegrityResult:
    """Fail closed when an operator asks to treat an excluded class as in-scope."""
    rel = normalize_relative_path(requested_relative)
    if is_excluded_relative_path(rel) or not path_in_included_scope(rel):
        # Public checkout and secrets are not under included prefixes
        return IntegrityResult(
            status="blocked",
            reason_codes=[REASON_SCOPE_AMBIGUOUS],
            summary=(
                "Request treats an excluded or out-of-contract path as backup "
                "scope; fail closed pending a new approved OpenSpec change."
            ),
            relative_paths_noted=[rel] if is_path_safe_relative(rel) else [],
        )
    return IntegrityResult(
        status="pass",
        reason_codes=[],
        summary="Path is within defined included scope.",
        relative_paths_noted=[rel],
    )
