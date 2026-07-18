"""Editorial backup restore and recovery drills (US-037).

Restores US-036 included-scope content from integrity-pass packages under
metadata/backups/ into dry-run plans, explicit fixture targets, or
confirmation-gated live mounts. Reuses US-036 verify/scope helpers. Does not
add FastAPI routes. n8n must not use Execute Command (ADR-0001).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from silverman_blog_linkedin.editorial_backup_integrity import (
    BACKUPS_RELATIVE,
    CONTENT_DIRNAME,
    MANIFEST_FILENAME,
    is_excluded_relative_path,
    is_path_safe_relative,
    package_dir,
    path_in_included_scope,
    verify_editorial_backup,
)
from silverman_blog_linkedin.file_reader import normalize_relative_path

RestoreStatus = Literal["pass", "fail", "blocked"]
RestoreMode = Literal["dry_run", "restore_drill", "live_restore"]

REASON_INTEGRITY_NOT_PASS = "restore_integrity_not_pass"
REASON_PACKAGE_MISSING = "restore_package_missing"
REASON_LIVE_CONFIRMATION_REQUIRED = "restore_live_confirmation_required"
REASON_TARGET_UNSAFE = "restore_target_unsafe"
REASON_SECRET_PATH_REFUSED = "restore_secret_path_refused"
REASON_POSTCHECK_HASH_MISMATCH = "restore_postcheck_hash_mismatch"
REASON_SCOPE_CLASS_INCOMPLETE = "restore_scope_class_incomplete"
REASON_PATH_UNSAFE = "restore_path_unsafe"
REASON_MANIFEST_UNREADABLE = "restore_manifest_unreadable"


@dataclass
class RestoreResult:
    status: RestoreStatus
    reason_codes: list[str] = field(default_factory=list)
    backup_id: str | None = None
    mode: RestoreMode = "dry_run"
    files_planned: int = 0
    files_restored: int = 0
    mismatch_count: int = 0
    relative_paths_noted: list[str] = field(default_factory=list)
    integrity_status: str | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "backup_id": self.backup_id,
            "mode": self.mode,
            "files_planned": self.files_planned,
            "files_restored": self.files_restored,
            "mismatch_count": self.mismatch_count,
            "relative_paths_noted": list(self.relative_paths_noted),
            "integrity_status": self.integrity_status,
            "summary": self.summary,
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _dedupe_reasons(codes: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def _cap_noted(paths: list[str], limit: int = 20) -> list[str]:
    noted: list[str] = []
    for item in paths:
        if item not in noted and is_path_safe_relative(item):
            noted.append(item)
        if len(noted) >= limit:
            break
    return noted


def _load_package_manifest(
    base_path: Path, backup_id: str
) -> tuple[dict[str, Any] | None, str | None]:
    pkg = package_dir(base_path, backup_id)
    manifest_path = pkg / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return None, REASON_MANIFEST_UNREADABLE
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, REASON_MANIFEST_UNREADABLE
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        return None, REASON_MANIFEST_UNREADABLE
    return data, None


def _resolve_under(root: Path, relative: str) -> Path | None:
    """Resolve relative under root; None if escape or unsafe."""
    if not is_path_safe_relative(relative):
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _plan_entries(
    content_root: Path, manifest: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Return (entries_to_restore, reason_codes, noted_paths)."""
    reasons: list[str] = []
    noted: list[str] = []
    planned: list[dict[str, Any]] = []
    content_resolved = content_root.resolve()

    for entry in manifest["files"]:
        if not isinstance(entry, dict):
            continue
        rel = entry.get("path")
        if not isinstance(rel, str):
            continue
        rel_norm = normalize_relative_path(rel)
        if not is_path_safe_relative(rel_norm):
            if REASON_PATH_UNSAFE not in reasons:
                reasons.append(REASON_PATH_UNSAFE)
            noted.append("(unsafe)")
            continue
        if is_excluded_relative_path(rel_norm):
            if REASON_SECRET_PATH_REFUSED not in reasons:
                reasons.append(REASON_SECRET_PATH_REFUSED)
            noted.append(rel_norm)
            continue
        if not path_in_included_scope(rel_norm):
            if REASON_SECRET_PATH_REFUSED not in reasons:
                reasons.append(REASON_SECRET_PATH_REFUSED)
            noted.append(rel_norm)
            continue

        src = _resolve_under(content_resolved, rel_norm)
        if src is None or not src.is_file():
            if REASON_SCOPE_CLASS_INCOMPLETE not in reasons:
                reasons.append(REASON_SCOPE_CLASS_INCOMPLETE)
            noted.append(rel_norm)
            continue

        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if not isinstance(expected_hash, str) or not isinstance(expected_size, int):
            if REASON_MANIFEST_UNREADABLE not in reasons:
                reasons.append(REASON_MANIFEST_UNREADABLE)
            noted.append(rel_norm)
            continue

        planned.append(
            {
                "path": rel_norm,
                "sha256": expected_hash,
                "size_bytes": expected_size,
                "source": src,
            }
        )

    return planned, reasons, noted


def _target_looks_like_package_host(base_path: Path, target_base: Path) -> bool:
    try:
        return target_base.resolve() == Path(base_path).resolve()
    except OSError:
        return False


def restore_editorial_backup(
    base_path: Path,
    backup_id: str,
    *,
    mode: RestoreMode = "dry_run",
    target_base: Path | None = None,
    live_confirmed: bool = False,
) -> RestoreResult:
    """Restore or plan restore from a US-036 package.

    Modes:
    - dry_run: validate + plan only; no writes
    - restore_drill: write into explicit target_base (fixture/staging)
    - live_restore: write into target (defaults to base_path); requires
      live_confirmed=True

    Never mutates packages under metadata/backups/. Never restores secrets.
    """
    root = Path(base_path).resolve()
    bid = normalize_relative_path(backup_id)
    if not bid or "/" in bid or "\\" in bid or not is_path_safe_relative(bid):
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_PACKAGE_MISSING],
            backup_id=None,
            mode=mode,
            summary="Backup id is missing or path-unsafe; restore blocked.",
        )

    pkg = package_dir(root, bid)
    if not pkg.is_dir():
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_PACKAGE_MISSING],
            backup_id=bid,
            mode=mode,
            summary="Backup package directory is missing; restore blocked.",
        )

    integrity = verify_editorial_backup(root, bid)
    if integrity.status != "pass":
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_INTEGRITY_NOT_PASS],
            backup_id=bid,
            mode=mode,
            integrity_status=integrity.status,
            relative_paths_noted=_cap_noted(list(integrity.relative_paths_noted)),
            summary=(
                "US-036 integrity is not pass; restore blocked "
                f"(integrity_status={integrity.status})."
            ),
        )

    if mode == "live_restore" and not live_confirmed:
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_LIVE_CONFIRMATION_REQUIRED],
            backup_id=bid,
            mode=mode,
            integrity_status="pass",
            summary=(
                "Live restore requires explicit confirmation "
                "(--i-understand-live-restore); restore blocked."
            ),
        )

    if mode in ("dry_run", "restore_drill", "live_restore"):
        if target_base is None:
            if mode == "live_restore":
                target_base = root
            else:
                return RestoreResult(
                    status="blocked",
                    reason_codes=[REASON_TARGET_UNSAFE],
                    backup_id=bid,
                    mode=mode,
                    integrity_status="pass",
                    summary=(
                        "Explicit target_base is required for dry-run and "
                        "restore-drill; restore blocked."
                    ),
                )
    assert target_base is not None
    try:
        target = Path(target_base).resolve()
    except OSError:
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_TARGET_UNSAFE],
            backup_id=bid,
            mode=mode,
            integrity_status="pass",
            summary="Target base path could not be resolved; restore blocked.",
        )

    # Fail closed: restore_drill / dry_run must not silently overwrite package host
    if mode in ("dry_run", "restore_drill") and _target_looks_like_package_host(
        root, target
    ):
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_TARGET_UNSAFE],
            backup_id=bid,
            mode=mode,
            integrity_status="pass",
            summary=(
                "Target resolves to the package host editorial base; use "
                "live_restore with explicit confirmation or a distinct "
                "fixture/staging target."
            ),
        )

    if mode == "live_restore" and not live_confirmed:
        # Defensive second gate
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_LIVE_CONFIRMATION_REQUIRED],
            backup_id=bid,
            mode=mode,
            integrity_status="pass",
            summary="Live restore confirmation missing; restore blocked.",
        )

    manifest, load_err = _load_package_manifest(root, bid)
    if load_err or manifest is None:
        return RestoreResult(
            status="blocked",
            reason_codes=[load_err or REASON_MANIFEST_UNREADABLE],
            backup_id=bid,
            mode=mode,
            integrity_status="pass",
            summary="Manifest unreadable after integrity pass; restore blocked.",
        )

    content_root = pkg / CONTENT_DIRNAME
    planned, plan_reasons, plan_noted = _plan_entries(content_root, manifest)
    if plan_reasons:
        # Secret/excluded/unsafe in package content → fail closed without writes
        status: RestoreStatus = (
            "blocked"
            if REASON_SECRET_PATH_REFUSED in plan_reasons
            or REASON_PATH_UNSAFE in plan_reasons
            else "fail"
        )
        return RestoreResult(
            status=status,
            reason_codes=_dedupe_reasons(plan_reasons),
            backup_id=bid,
            mode=mode,
            files_planned=len(planned),
            integrity_status="pass",
            relative_paths_noted=_cap_noted(plan_noted),
            summary=(
                "Restore refused before writes: "
                + ", ".join(_dedupe_reasons(plan_reasons))
            ),
        )

    files_planned = len(planned)
    if mode == "dry_run":
        return RestoreResult(
            status="pass",
            reason_codes=[],
            backup_id=bid,
            mode=mode,
            files_planned=files_planned,
            files_restored=0,
            integrity_status="pass",
            summary=(
                f"Dry-run validated: {files_planned} file(s) planned; "
                "no target writes."
            ),
        )

    # Ensure we never write into the backup package tree as "editorial content"
    backups_resolved = (root / BACKUPS_RELATIVE).resolve()
    try:
        target.relative_to(backups_resolved)
        inside_backups = True
    except ValueError:
        inside_backups = False
    if inside_backups:
        return RestoreResult(
            status="blocked",
            reason_codes=[REASON_TARGET_UNSAFE],
            backup_id=bid,
            mode=mode,
            files_planned=files_planned,
            integrity_status="pass",
            summary=(
                "Target is inside metadata/backups/; restore must not mutate "
                "backup packages."
            ),
        )

    target.mkdir(parents=True, exist_ok=True)
    restored = 0
    mismatch = 0
    fail_reasons: list[str] = []
    noted: list[str] = []

    for item in planned:
        rel = item["path"]
        # Double-check exclusions at write time
        if (
            is_excluded_relative_path(rel)
            or not path_in_included_scope(rel)
            or rel == BACKUPS_RELATIVE
            or rel.startswith(BACKUPS_RELATIVE + "/")
        ):
            if REASON_SECRET_PATH_REFUSED not in fail_reasons:
                fail_reasons.append(REASON_SECRET_PATH_REFUSED)
            noted.append(rel)
            continue

        dest = _resolve_under(target, rel)
        if dest is None:
            if REASON_PATH_UNSAFE not in fail_reasons:
                fail_reasons.append(REASON_PATH_UNSAFE)
            noted.append(rel)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item["source"], dest)
        restored += 1

        actual_size = dest.stat().st_size
        actual_hash = _sha256_file(dest)
        if actual_size != item["size_bytes"] or actual_hash != item["sha256"]:
            if REASON_POSTCHECK_HASH_MISMATCH not in fail_reasons:
                fail_reasons.append(REASON_POSTCHECK_HASH_MISMATCH)
            noted.append(rel)
            mismatch += 1
            continue

    if fail_reasons:
        return RestoreResult(
            status="fail",
            reason_codes=_dedupe_reasons(fail_reasons),
            backup_id=bid,
            mode=mode,
            files_planned=files_planned,
            files_restored=restored,
            mismatch_count=mismatch,
            integrity_status="pass",
            relative_paths_noted=_cap_noted(noted),
            summary="Restore failed: " + ", ".join(_dedupe_reasons(fail_reasons)),
        )

    # Scope completeness: every planned file should have been restored
    if restored != files_planned:
        return RestoreResult(
            status="fail",
            reason_codes=[REASON_SCOPE_CLASS_INCOMPLETE],
            backup_id=bid,
            mode=mode,
            files_planned=files_planned,
            files_restored=restored,
            integrity_status="pass",
            relative_paths_noted=_cap_noted(noted),
            summary="Restore incomplete relative to package manifest plan.",
        )

    return RestoreResult(
        status="pass",
        reason_codes=[],
        backup_id=bid,
        mode=mode,
        files_planned=files_planned,
        files_restored=restored,
        mismatch_count=0,
        integrity_status="pass",
        summary=(
            f"Restore {mode} passed: {restored} file(s) restored with "
            "postcheck OK."
        ),
    )
