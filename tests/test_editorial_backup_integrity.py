"""US-036 editorial backup scope, retention, and integrity tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from silverman_blog_linkedin.editorial_backup_integrity import (
    BACKUPS_RELATIVE,
    CONTENT_DIRNAME,
    DEFAULT_RETENTION_KEEP_COUNT,
    INCLUDED_SCOPE_CLASSES,
    MANIFEST_FILENAME,
    REASON_HASH_MISMATCH,
    REASON_PACKAGE_MISSING,
    REASON_PATH_UNSAFE,
    REASON_SCOPE_AMBIGUOUS,
    REASON_SCOPE_CLASS_MISSING,
    create_editorial_backup,
    is_excluded_relative_path,
    is_path_safe_relative,
    package_dir,
    prune_editorial_backups,
    refuse_excluded_scope_expansion,
    verify_editorial_backup,
)
from tests.conftest import create_full_layout

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_DOC = (
    REPO_ROOT
    / "docs"
    / "operations"
    / "editorial-backup-scope-retention-integrity.md"
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_manifest(pkg: Path, manifest: dict) -> None:
    (pkg / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _seed_editorial_sources(base: Path) -> None:
    create_full_layout(base)
    (base / "blog-posts/ready/sample.md").write_text(
        "# Sample\n\nBody text.\n", encoding="utf-8"
    )
    (base / "metadata/campaigns/camp-1.json").write_text(
        '{"campaign_id":"camp-1","state":"ready"}\n', encoding="utf-8"
    )
    (base / "metadata/runs/run-1.json").write_text(
        '{"run_id":"run-1"}\n', encoding="utf-8"
    )
    (base / "editorial-calendar/calendar.json").write_text(
        '{"items":[]}\n', encoding="utf-8"
    )
    (base / "prompts/system.md").write_text("prompt\n", encoding="utf-8")
    (base / "linkedin-posts/review/variant.md").write_text(
        "linkedin body\n", encoding="utf-8"
    )


def _assert_secret_safe(payload: dict) -> None:
    serialized = json.dumps(payload)
    assert "API_KEY" not in serialized
    assert "Bearer " not in serialized
    assert "sk-" not in serialized
    assert "super-secret" not in serialized
    assert "\n# Sample" not in serialized
    assert "linkedin body" not in serialized
    # No absolute home-style secret paths
    assert "/Users/" not in serialized
    assert "/home/" not in serialized
    assert "content_body" not in payload
    assert "markdown_content" not in payload


class TestPathSafety:
    def test_relative_safe(self) -> None:
        assert is_path_safe_relative("blog-posts/ready/a.md")

    def test_traversal_unsafe(self) -> None:
        assert not is_path_safe_relative("../etc/passwd")
        assert not is_path_safe_relative("blog-posts/../../secret")

    def test_absolute_unsafe(self) -> None:
        assert not is_path_safe_relative("/etc/passwd")
        assert not is_path_safe_relative("C:/secrets/token")


class TestIntegrityVerify:
    def test_pass_fixture(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-pass01")
        result = verify_editorial_backup(base, created["backup_id"])
        assert result.status == "pass"
        assert result.reason_codes == []
        assert result.files_checked >= 1
        _assert_secret_safe(result.to_dict())

    def test_hash_mismatch_fail(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-hash01")
        pkg = package_dir(base, created["backup_id"])
        content_file = pkg / CONTENT_DIRNAME / "blog-posts/ready/sample.md"
        original = content_file.read_bytes()
        # Same length, different bytes so size matches and hash fails
        tampered = (b"X" * len(original)) if original else b"X"
        assert len(tampered) == len(original)
        content_file.write_bytes(tampered)
        result = verify_editorial_backup(base, created["backup_id"])
        assert result.status == "fail"
        assert REASON_HASH_MISMATCH in result.reason_codes
        _assert_secret_safe(result.to_dict())

    def test_missing_package_blocked(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        create_full_layout(base)
        result = verify_editorial_backup(base, "editorial-backup-missing01")
        assert result.status == "blocked"
        assert REASON_PACKAGE_MISSING in result.reason_codes
        _assert_secret_safe(result.to_dict())

    def test_path_traversal_fail(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        create_full_layout(base)
        bid = "editorial-backup-trav01"
        pkg = package_dir(base, bid)
        (pkg / CONTENT_DIRNAME).mkdir(parents=True)
        manifest = {
            "schema_version": "1",
            "backup_id": bid,
            "created_at_utc": "2026-07-18T12:00:00Z",
            "scope": {
                "included_classes": list(INCLUDED_SCOPE_CLASSES),
                "empty_classes": {
                    c: "no_files_present" for c in INCLUDED_SCOPE_CLASSES
                },
            },
            "retention": {"keep_count": 7},
            "files": [
                {
                    "path": "../outside.txt",
                    "sha256": _sha256_bytes(b"x"),
                    "size_bytes": 1,
                }
            ],
        }
        _write_manifest(pkg, manifest)
        result = verify_editorial_backup(base, bid)
        assert result.status == "fail"
        assert REASON_PATH_UNSAFE in result.reason_codes
        _assert_secret_safe(result.to_dict())

    def test_secret_safe_result_shape(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        # Place a secret-like file in source — builder must exclude it
        (base / "blog-posts/ready/.env").write_text(
            "SILVERMAN_BLOG_LINKEDIN_API_KEY=super-secret-token\n",
            encoding="utf-8",
        )
        created = create_editorial_backup(base, backup_id="editorial-backup-sec01")
        pkg = package_dir(base, created["backup_id"])
        assert not (pkg / CONTENT_DIRNAME / "blog-posts/ready/.env").exists()
        result = verify_editorial_backup(base, created["backup_id"])
        payload = result.to_dict()
        _assert_secret_safe(payload)
        assert "super-secret-token" not in json.dumps(payload)
        assert "content_body" not in payload
        assert "markdown_content" not in payload


class TestBuilderAndPrune:
    def test_builder_writes_only_under_backups(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        ready = base / "blog-posts/ready/sample.md"
        before = ready.read_bytes()
        before_sha = _sha256_bytes(before)

        created = create_editorial_backup(base, backup_id="editorial-backup-bld01")
        assert created["package_relative"].startswith(BACKUPS_RELATIVE + "/")
        pkg = package_dir(base, created["backup_id"])
        assert (pkg / MANIFEST_FILENAME).is_file()
        assert (pkg / CONTENT_DIRNAME / "blog-posts/ready/sample.md").is_file()

        assert ready.read_bytes() == before
        assert _sha256_bytes(ready.read_bytes()) == before_sha
        # Source trees outside backups unchanged (no new files under campaigns
        # from builder aside from what we seeded)
        assert list((base / "metadata/campaigns").iterdir())

    def test_builder_excludes_nested_backups_and_junk(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        nested = base / "metadata/backups/old-pkg/manifest.json"
        nested.parent.mkdir(parents=True, exist_ok=True)
        nested.write_text("{}\n", encoding="utf-8")
        (base / "blog-posts/ready/.DS_Store").write_bytes(b"junk")
        (base / "blog-posts/ready/note.tmp").write_text("tmp\n", encoding="utf-8")

        created = create_editorial_backup(base, backup_id="editorial-backup-excl01")
        content = package_dir(base, created["backup_id"]) / CONTENT_DIRNAME
        assert not (content / "metadata/backups").exists()
        assert not (content / "blog-posts/ready/.DS_Store").exists()
        assert not (content / "blog-posts/ready/note.tmp").exists()
        assert is_excluded_relative_path("metadata/backups/old-pkg/manifest.json")

    def test_prune_keeps_fail_and_stays_in_backups(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        sentinel = base / "blog-posts/ready/sample.md"
        sentinel_bytes = sentinel.read_bytes()

        # Create more than keep_count passing packages
        ids: list[str] = []
        for i in range(DEFAULT_RETENTION_KEEP_COUNT + 2):
            bid = f"editorial-backup-20260718T{i:02d}0000Z-aaaaaa"
            create_editorial_backup(base, backup_id=bid)
            ids.append(bid)

        # One failed package (tamper after create)
        fail_id = "editorial-backup-20260718T990000Z-ffff01"
        create_editorial_backup(base, backup_id=fail_id)
        fail_pkg = package_dir(base, fail_id)
        target = fail_pkg / CONTENT_DIRNAME / "blog-posts/ready/sample.md"
        target.write_text("# broken\n", encoding="utf-8")
        assert verify_editorial_backup(base, fail_id).status == "fail"

        outside = base / "metadata/campaigns/camp-1.json"
        outside_before = outside.read_bytes()

        outcome = prune_editorial_backups(
            base, keep_count=DEFAULT_RETENTION_KEEP_COUNT, dry_run=False
        )
        assert fail_id in outcome["retained_failed_or_blocked"]
        assert package_dir(base, fail_id).is_dir()
        assert len(outcome["kept"]) == DEFAULT_RETENTION_KEEP_COUNT
        assert len(outcome["deleted"]) >= 1
        for deleted_id in outcome["deleted"]:
            assert not package_dir(base, deleted_id).exists()

        assert sentinel.read_bytes() == sentinel_bytes
        assert outside.read_bytes() == outside_before

    def test_prune_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        for i in range(3):
            create_editorial_backup(
                base, backup_id=f"editorial-backup-20260718T{i:02d}0000Z-dryrun"
            )
        outcome = prune_editorial_backups(base, keep_count=1, dry_run=True)
        assert outcome["dry_run"] is True
        assert len(outcome["deleted"]) == 2
        for bid in outcome["deleted"]:
            assert package_dir(base, bid).is_dir()


class TestScopeFailClosed:
    def test_refuse_public_checkout_and_secrets(self) -> None:
        for path in (
            ".env",
            "secrets.json",
            "metadata/backups/x/manifest.json",
        ):
            result = refuse_excluded_scope_expansion(path)
            assert result.status == "blocked"
            assert REASON_SCOPE_AMBIGUOUS in result.reason_codes

    def test_missing_scope_class_without_empty_declaration_fails(
        self, tmp_path: Path
    ) -> None:
        base = tmp_path / "editorial"
        create_full_layout(base)
        bid = "editorial-backup-scope01"
        pkg = package_dir(base, bid)
        (pkg / CONTENT_DIRNAME).mkdir(parents=True)
        # Intentionally omit empty_classes — fail closed
        manifest = {
            "schema_version": "1",
            "backup_id": bid,
            "created_at_utc": "2026-07-18T12:00:00Z",
            "scope": {"included_classes": list(INCLUDED_SCOPE_CLASSES)},
            "retention": {"keep_count": 7},
            "files": [],
        }
        _write_manifest(pkg, manifest)
        result = verify_editorial_backup(base, bid)
        assert result.status == "fail"
        assert REASON_SCOPE_CLASS_MISSING in result.reason_codes


class TestPolicyPresence:
    def test_operator_policy_doc_exists_with_required_phrases(self) -> None:
        assert POLICY_DOC.is_file()
        text = POLICY_DOC.read_text(encoding="utf-8")
        required = (
            "US-036",
            "US-037",
            "backup scope",
            "retention",
            "integrity",
            "metadata/backups",
            "pass",
            "fail",
            "blocked",
            "secrets",
            "GitHub Pages",
            "restore",
            "7 most recent",
        )
        lower = text.lower()
        for phrase in required:
            assert phrase.lower() in lower, f"missing phrase: {phrase}"


class TestHealthNotBackupOps:
    def test_health_module_unchanged_for_backup_ops(self) -> None:
        """GET /health must not import backup create/verify/prune/restore."""
        main_src = (
            REPO_ROOT / "src" / "silverman_blog_linkedin" / "main.py"
        ).read_text(encoding="utf-8")
        assert "editorial_backup_integrity" not in main_src
        assert "create_editorial_backup" not in main_src
        assert "prune_editorial_backups" not in main_src
