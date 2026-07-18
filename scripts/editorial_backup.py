#!/usr/bin/env python3
"""CLI for editorial backup create / verify / prune (US-036) and restore (US-037).

No FastAPI routes. n8n must not invoke this via Execute Command (ADR-0001).
Live restore is fail-closed without --i-understand-live-restore.
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
from silverman_blog_linkedin.editorial_backup_restore import restore_editorial_backup


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _restore_exit(status: str) -> int:
    if status == "pass":
        return 0
    if status == "blocked":
        return 2
    return 1


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


def cmd_restore_dry_run(args: argparse.Namespace) -> int:
    result = restore_editorial_backup(
        Path(args.base_path),
        args.backup_id,
        mode="dry_run",
        target_base=Path(args.target_base),
    )
    _print_json(result.to_dict())
    return _restore_exit(result.status)


def cmd_restore_drill(args: argparse.Namespace) -> int:
    result = restore_editorial_backup(
        Path(args.base_path),
        args.backup_id,
        mode="restore_drill",
        target_base=Path(args.target_base),
    )
    _print_json(result.to_dict())
    return _restore_exit(result.status)


def cmd_restore(args: argparse.Namespace) -> int:
    target = Path(args.target_base) if args.target_base else Path(args.base_path)
    result = restore_editorial_backup(
        Path(args.base_path),
        args.backup_id,
        mode="live_restore",
        target_base=target,
        live_confirmed=bool(args.i_understand_live_restore),
    )
    _print_json(result.to_dict())
    return _restore_exit(result.status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Editorial backup (US-036 create/verify/prune) and restore "
            "(US-037 dry-run / restore-drill / gated live restore). "
            "No FastAPI routes; n8n must not use Execute Command (ADR-0001)."
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

    dry_p = sub.add_parser(
        "restore-dry-run",
        help="US-037: plan restore against a pass-integrity package (no writes)",
    )
    dry_p.add_argument("--base-path", required=True)
    dry_p.add_argument("--backup-id", required=True)
    dry_p.add_argument(
        "--target-base",
        required=True,
        help="Explicit fixture/staging target (must differ from base-path)",
    )
    dry_p.set_defaults(func=cmd_restore_dry_run)

    drill_p = sub.add_parser(
        "restore-drill",
        help="US-037: restore into an explicit fixture/staging target",
    )
    drill_p.add_argument("--base-path", required=True)
    drill_p.add_argument("--backup-id", required=True)
    drill_p.add_argument(
        "--target-base",
        required=True,
        help="Explicit fixture/staging target (must differ from base-path)",
    )
    drill_p.set_defaults(func=cmd_restore_drill)

    live_p = sub.add_parser(
        "restore",
        help=(
            "US-037: live restore (fail-closed; requires "
            "--i-understand-live-restore)"
        ),
    )
    live_p.add_argument("--base-path", required=True)
    live_p.add_argument("--backup-id", required=True)
    live_p.add_argument(
        "--target-base",
        default=None,
        help="Live editorial base to overwrite (default: --base-path)",
    )
    live_p.add_argument(
        "--i-understand-live-restore",
        action="store_true",
        help="Explicit confirmation required for live production mutation",
    )
    live_p.set_defaults(func=cmd_restore)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
