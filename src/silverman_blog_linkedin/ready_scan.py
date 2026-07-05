"""Scan and validate Markdown candidates in blog-posts/ready/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

READY_RELATIVE = "blog-posts/ready"


@dataclass(frozen=True)
class ScanResult:
    valid_files: list[dict]
    invalid_files: list[dict]
    ignored_files: list[dict]
    candidate_count: int
    valid_count: int
    invalid_count: int
    ignored_count: int


def _empty_scan_result() -> ScanResult:
    return ScanResult(
        valid_files=[],
        invalid_files=[],
        ignored_files=[],
        candidate_count=0,
        valid_count=0,
        invalid_count=0,
        ignored_count=0,
    )


def _is_md_suffix(path: Path) -> bool:
    return path.suffix.lower() == ".md"


def scan_ready_folder(base_path: Path) -> ScanResult:
    """Non-recursively scan blog-posts/ready for Markdown candidates."""
    ready_dir = base_path / READY_RELATIVE
    if not ready_dir.is_dir():
        return _empty_scan_result()

    ready_resolved = ready_dir.resolve()
    valid_files: list[dict] = []
    invalid_files: list[dict] = []
    ignored_files: list[dict] = []

    for entry in sorted(ready_dir.iterdir(), key=lambda p: p.name):
        name = entry.name
        relative_path = f"{READY_RELATIVE}/{name}"

        if entry.is_dir():
            ignored_files.append(
                {
                    "filename": name,
                    "relative_path": relative_path,
                    "reason": "subdirectory",
                }
            )
            continue

        if not entry.is_file():
            continue

        if not _is_md_suffix(entry):
            ignored_files.append(
                {
                    "filename": name,
                    "relative_path": relative_path,
                    "reason": "non_markdown",
                }
            )
            continue

        resolved = entry.resolve()
        if not resolved.is_relative_to(ready_resolved):
            invalid_files.append(
                {
                    "filename": name,
                    "relative_path": relative_path,
                    "errors": ["path_outside_ready"],
                }
            )
            continue

        errors: list[str] = []
        if not entry.exists():
            errors.append("exists")
        if not entry.is_file():
            errors.append("is_regular_file")
        if not _is_md_suffix(entry):
            errors.append("extension_md")

        size_bytes = 0
        try:
            size_bytes = entry.stat().st_size
            entry.read_bytes()
        except OSError:
            errors.append("readable")

        if not errors and size_bytes == 0:
            errors.append("not_empty")

        if errors:
            invalid_files.append(
                {
                    "filename": name,
                    "relative_path": relative_path,
                    "errors": errors,
                }
            )
        else:
            valid_files.append(
                {
                    "filename": name,
                    "relative_path": relative_path,
                    "size_bytes": size_bytes,
                }
            )

    candidate_count = len(valid_files) + len(invalid_files)
    return ScanResult(
        valid_files=valid_files,
        invalid_files=invalid_files,
        ignored_files=ignored_files,
        candidate_count=candidate_count,
        valid_count=len(valid_files),
        invalid_count=len(invalid_files),
        ignored_count=len(ignored_files),
    )
