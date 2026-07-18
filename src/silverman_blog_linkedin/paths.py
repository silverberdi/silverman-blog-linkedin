"""Editorial folder layout validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EXPECTED_FOLDERS: tuple[str, ...] = (
    "blog-posts/ready",
    "blog-posts/queued",
    "blog-posts/processed",
    "blog-posts/error",
    "linkedin-posts/review",
    "linkedin-posts/approved",
    "linkedin-posts/published",
    "metadata/runs",
    "metadata/campaigns",
    # Designated root for editorial backup packages (US-036). Health/folder
    # validation only checks directory presence — it does not create, verify,
    # prune, or restore backup packages.
    "metadata/backups",
    "prompts",
    "editorial-calendar",
)


@dataclass(frozen=True)
class FolderStatus:
    exists: bool
    is_directory: bool

    def to_dict(self) -> dict[str, bool]:
        return {"exists": self.exists, "is_directory": self.is_directory}


@dataclass(frozen=True)
class FolderValidationResult:
    folders: dict[str, FolderStatus]
    folders_ready: bool


def _check_folder(base_path: Path, relative: str) -> FolderStatus:
    path = base_path / relative
    exists = path.exists()
    is_directory = path.is_dir() if exists else False
    return FolderStatus(exists=exists, is_directory=is_directory)


def validate_folders(base_path: Path) -> FolderValidationResult:
    """Read-only validation of expected editorial folders under base_path."""
    if not base_path.exists() or not base_path.is_dir():
        folders = {
            relative: FolderStatus(exists=False, is_directory=False)
            for relative in EXPECTED_FOLDERS
        }
        return FolderValidationResult(folders=folders, folders_ready=False)

    folders = {
        relative: _check_folder(base_path, relative)
        for relative in EXPECTED_FOLDERS
    }
    folders_ready = all(
        status.exists and status.is_directory for status in folders.values()
    )
    return FolderValidationResult(folders=folders, folders_ready=folders_ready)
