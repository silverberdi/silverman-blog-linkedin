"""US-037 editorial backup restore drills and recovery procedure tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from silverman_blog_linkedin.editorial_backup_integrity import (
    CONTENT_DIRNAME,
    MANIFEST_FILENAME,
    IntegrityResult,
    create_editorial_backup,
    package_dir,
    verify_editorial_backup,
)
from silverman_blog_linkedin.editorial_backup_restore import (
    REASON_INTEGRITY_NOT_PASS,
    REASON_LIVE_CONFIRMATION_REQUIRED,
    REASON_PACKAGE_MISSING,
    REASON_POSTCHECK_HASH_MISMATCH,
    REASON_SECRET_PATH_REFUSED,
    restore_editorial_backup,
)
from tests.conftest import create_full_layout

REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_DOC = (
    REPO_ROOT / "docs" / "operations" / "editorial-backup-restore-recovery.md"
)
US036_POLICY = (
    REPO_ROOT
    / "docs"
    / "operations"
    / "editorial-backup-scope-retention-integrity.md"
)


def _seed_editorial_sources(base: Path) -> None:
    create_full_layout(base)
    (base / "blog-posts/ready/sample.md").write_text(
        "# Sample\n\nBody text.\n", encoding="utf-8"
    )
    (base / "blog-posts/ready/hero.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
    )
    (base / "metadata/campaigns/camp-1.json").write_text(
        '{"campaign_id":"camp-1","state":"ready"}\n', encoding="utf-8"
    )
    (base / "metadata/runs/run-1.json").write_text(
        '{"run_id":"run-1"}\n', encoding="utf-8"
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
    assert "/Users/" not in serialized
    assert "/home/" not in serialized
    assert "content_body" not in payload
    assert "markdown_content" not in payload


class TestRestoreDrillPass:
    def test_fixture_restore_drill_pass_covers_protected_classes(
        self, tmp_path: Path
    ) -> None:
        base = tmp_path / "editorial"
        target = tmp_path / "fixture-target"
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-rst01")
        assert verify_editorial_backup(base, created["backup_id"]).status == "pass"

        result = restore_editorial_backup(
            base,
            created["backup_id"],
            mode="restore_drill",
            target_base=target,
        )
        assert result.status == "pass"
        assert result.reason_codes == []
        assert result.files_restored >= 1
        _assert_secret_safe(result.to_dict())

        assert (target / "metadata/campaigns/camp-1.json").is_file()
        assert (target / "linkedin-posts/review/variant.md").is_file()
        assert (target / "blog-posts/ready/hero.png").is_file()
        assert (target / "blog-posts/ready/sample.md").read_text(
            encoding="utf-8"
        ) == "# Sample\n\nBody text.\n"
        # Backup packages must not be mutated or nested as source content
        assert not (target / "metadata/backups").exists()
        assert package_dir(base, created["backup_id"]).is_dir()


class TestRestoreBlockedAndDryRun:
    def test_integrity_not_pass_blocks_with_no_writes(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        target = tmp_path / "fixture-target"
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-rst02")
        pkg = package_dir(base, created["backup_id"])
        sample = pkg / CONTENT_DIRNAME / "blog-posts/ready/sample.md"
        original = sample.read_bytes()
        sample.write_bytes(b"X" * len(original))
        assert verify_editorial_backup(base, created["backup_id"]).status == "fail"

        result = restore_editorial_backup(
            base,
            created["backup_id"],
            mode="restore_drill",
            target_base=target,
        )
        assert result.status == "blocked"
        assert REASON_INTEGRITY_NOT_PASS in result.reason_codes
        assert not target.exists() or not any(target.rglob("*"))
        _assert_secret_safe(result.to_dict())

    def test_missing_package_blocked(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        target = tmp_path / "fixture-target"
        create_full_layout(base)
        result = restore_editorial_backup(
            base,
            "editorial-backup-missing-rst",
            mode="restore_drill",
            target_base=target,
        )
        assert result.status == "blocked"
        assert REASON_PACKAGE_MISSING in result.reason_codes
        _assert_secret_safe(result.to_dict())

    def test_dry_run_does_not_mutate(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        target = tmp_path / "fixture-target"
        target.mkdir()
        marker = target / "pre-existing.txt"
        marker.write_text("keep\n", encoding="utf-8")
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-rst03")

        result = restore_editorial_backup(
            base,
            created["backup_id"],
            mode="dry_run",
            target_base=target,
        )
        assert result.status == "pass"
        assert result.files_restored == 0
        assert result.files_planned >= 1
        assert marker.read_text(encoding="utf-8") == "keep\n"
        assert not (target / "blog-posts").exists()
        _assert_secret_safe(result.to_dict())

    def test_live_without_confirmation_blocked(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-rst04")
        before = (base / "blog-posts/ready/sample.md").read_bytes()

        result = restore_editorial_backup(
            base,
            created["backup_id"],
            mode="live_restore",
            target_base=base,
            live_confirmed=False,
        )
        assert result.status == "blocked"
        assert REASON_LIVE_CONFIRMATION_REQUIRED in result.reason_codes
        assert (base / "blog-posts/ready/sample.md").read_bytes() == before
        _assert_secret_safe(result.to_dict())


class TestSecretRefusalAndReportShape:
    def test_secret_path_refused_when_present_despite_verify_patch(
        self, tmp_path: Path
    ) -> None:
        base = tmp_path / "editorial"
        target = tmp_path / "fixture-target"
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-rst05")
        pkg = package_dir(base, created["backup_id"])
        secret_rel = "blog-posts/ready/.env"
        secret_path = pkg / CONTENT_DIRNAME / secret_rel
        secret_path.write_text(
            "SILVERMAN_BLOG_LINKEDIN_API_KEY=super-secret-token\n",
            encoding="utf-8",
        )
        manifest_path = pkg / MANIFEST_FILENAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].append(
            {
                "path": secret_rel,
                "sha256": "0" * 64,
                "size_bytes": secret_path.stat().st_size,
            }
        )
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with patch(
            "silverman_blog_linkedin.editorial_backup_restore.verify_editorial_backup",
            return_value=IntegrityResult(
                status="pass",
                reason_codes=[],
                backup_id=created["backup_id"],
                summary="patched pass",
            ),
        ):
            result = restore_editorial_backup(
                base,
                created["backup_id"],
                mode="restore_drill",
                target_base=target,
            )

        assert result.status in ("fail", "blocked")
        assert REASON_SECRET_PATH_REFUSED in result.reason_codes
        assert not (target / secret_rel).exists()
        payload = result.to_dict()
        _assert_secret_safe(payload)
        assert "super-secret-token" not in json.dumps(payload)

    def test_postcheck_hash_mismatch_fails(self, tmp_path: Path) -> None:
        base = tmp_path / "editorial"
        target = tmp_path / "fixture-target"
        _seed_editorial_sources(base)
        created = create_editorial_backup(base, backup_id="editorial-backup-rst06")

        real_copy = __import__("shutil").copy2

        def _corrupt_copy(src: Path, dst: Path) -> None:
            real_copy(src, dst)
            data = Path(dst).read_bytes()
            Path(dst).write_bytes(b"Y" * len(data) if data else b"Y")

        with patch(
            "silverman_blog_linkedin.editorial_backup_restore.shutil.copy2",
            side_effect=_corrupt_copy,
        ):
            result = restore_editorial_backup(
                base,
                created["backup_id"],
                mode="restore_drill",
                target_base=target,
            )

        assert result.status == "fail"
        assert REASON_POSTCHECK_HASH_MISMATCH in result.reason_codes
        _assert_secret_safe(result.to_dict())


class TestRecoveryPolicyPresence:
    def test_recovery_procedure_doc_exists_with_required_phrases(self) -> None:
        assert RECOVERY_DOC.is_file()
        text = RECOVERY_DOC.read_text(encoding="utf-8")
        required = (
            "US-037",
            "US-036",
            "integrity",
            "pass",
            "fail",
            "blocked",
            "restore",
            "fail-closed",
            "confirmation",
            "secrets",
            "GitHub Pages",
            "dry-run",
            "fixture",
            "calendar",
            "campaigns",
            "LinkedIn",
            "ADR-0001",
            "BL-014",
        )
        lower = text.lower()
        for phrase in required:
            assert phrase.lower() in lower, f"missing phrase: {phrase}"

    def test_us036_policy_points_to_us037_recovery(self) -> None:
        text = US036_POLICY.read_text(encoding="utf-8")
        assert "editorial-backup-restore-recovery.md" in text
        assert "US-037" in text


class TestNoPrimaryHttpRestore:
    def test_main_does_not_import_restore(self) -> None:
        main_src = (
            REPO_ROOT / "src" / "silverman_blog_linkedin" / "main.py"
        ).read_text(encoding="utf-8")
        assert "editorial_backup_restore" not in main_src
        assert "restore_editorial_backup" not in main_src
