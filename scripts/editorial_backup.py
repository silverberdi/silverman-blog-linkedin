#!/usr/bin/env python3
"""CLI for editorial backup create / verify / prune (US-036).

No FastAPI routes. Does not restore source editorial trees (US-037).
n8n must not invoke this via Execute Command (ADR-0001).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from silverman_blog_linkedin.editorial_backup_integrity import (
    DEFAULT_RETENTION_KEEP_COUNT,
    create_editorial_backup,
    prune_editorial_backups,
    verify_editorial_backup,
)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_verify(args: argparse.Namespace) -> int:
    result = verify_editorial_backup(Path(args.base_path), args.backup_id)
    _print_json(result.to_dict())
    if result.status == "pass":
        return 0
    if result.status == "blocked":
        return 2
    return 1


def cmd_create(args: argparse.Namespace) -> int:
    created = create_editorial_backup(
        Path(args.base_path),
        backup_id=args.backup_id,
        keep_count=args.keep_count,
    )
    # Verify immediately so operators see integrity outcome
    result = verify_editorial_backup(Path(args.base_path), created["backup_id"])
    _print_json({"create": created, "integrity": result.to_dict()})
    return 0 if result.status == "pass" else 1


def cmd_prune(args: argparse.Namespace) -> int:
    outcome = prune_editorial_backups(
        Path(args.base_path),
        keep_count=args.keep_count,
        dry_run=args.dry_run,
    )
    _print_json(outcome)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Editorial backup scope/retention/integrity (US-036). "
            "Does not restore production editorial state (US-037)."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify_p = sub.add_parser("verify", help="Verify backup package integrity")
    verify_p.add_argument(
        "--base-path",
        required=True,
        help="Editorial base path (SILVERMAN_BLOG_LINKEDIN_BASE_PATH)",
    )
    verify_p.add_argument(
        "--backup-id",
        required=True,
        help="Package directory name under metadata/backups/",
    )
    verify_p.set_defaults(func=cmd_verify)

    create_p = sub.add_parser(
        "create",
        help="Copy included scope into metadata/backups/<backup_id>/ only",
    )
    create_p.add_argument("--base-path", required=True)
    create_p.add_argument(
        "--backup-id",
        default=None,
        help="Optional package id; default is UTC-sortable generated id",
    )
    create_p.add_argument(
        "--keep-count",
        type=int,
        default=DEFAULT_RETENTION_KEEP_COUNT,
        help="Retention keep_count recorded in manifest (default 7)",
    )
    create_p.set_defaults(func=cmd_create)

    prune_p = sub.add_parser(
        "prune",
        help="Prune older pass packages under metadata/backups/ only",
    )
    prune_p.add_argument("--base-path", required=True)
    prune_p.add_argument(
        "--keep-count",
        type=int,
        default=DEFAULT_RETENTION_KEEP_COUNT,
    )
    prune_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report candidates without deleting",
    )
    prune_p.set_defaults(func=cmd_prune)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
