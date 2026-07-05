"""Tests for editorial folder validation."""

from pathlib import Path

from silverman_blog_linkedin.paths import EXPECTED_FOLDERS, validate_folders


def _create_full_layout(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for relative in EXPECTED_FOLDERS:
        (base / relative).mkdir(parents=True, exist_ok=True)


def test_all_folders_present(tmp_path):
    base = tmp_path / "editorial"
    _create_full_layout(base)

    result = validate_folders(base)

    assert result.folders_ready is True
    assert len(result.folders) == len(EXPECTED_FOLDERS)
    for relative in EXPECTED_FOLDERS:
        status = result.folders[relative]
        assert status.exists is True
        assert status.is_directory is True


def test_missing_folder(tmp_path):
    base = tmp_path / "editorial"
    _create_full_layout(base)
    missing = EXPECTED_FOLDERS[0]
    (base / missing).rmdir()

    result = validate_folders(base)

    assert result.folders_ready is False
    assert result.folders[missing].exists is False
    assert result.folders[missing].is_directory is False


def test_missing_base_path(tmp_path):
    base = tmp_path / "nonexistent"

    result = validate_folders(base)

    assert result.folders_ready is False
    for relative in EXPECTED_FOLDERS:
        status = result.folders[relative]
        assert status.exists is False
        assert status.is_directory is False


def test_file_instead_of_directory(tmp_path):
    base = tmp_path / "editorial"
    _create_full_layout(base)
    target = EXPECTED_FOLDERS[0]
    (base / target).rmdir()
    (base / target).write_text("not a directory")

    result = validate_folders(base)

    assert result.folders_ready is False
    assert result.folders[target].exists is True
    assert result.folders[target].is_directory is False
