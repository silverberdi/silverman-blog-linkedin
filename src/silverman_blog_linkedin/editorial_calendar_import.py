"""Operator-gated import of legacy editorial-calendar/calendar.json into the DB store."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_RELATIVE_PATH,
    CALENDAR_SCHEMA_INVALID,
    validate_calendar_document,
)
from silverman_blog_linkedin.editorial_calendar_store import (
    CALENDAR_STORE_UNAVAILABLE,
    get_calendar_store,
)


def load_legacy_calendar_file(base_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = base_path / CALENDAR_RELATIVE_PATH
    if not path.is_file():
        return None, ["calendar_file_not_found"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, [CALENDAR_SCHEMA_INVALID]
    if not isinstance(data, dict):
        return None, [CALENDAR_SCHEMA_INVALID]
    errors = validate_calendar_document(data)
    if errors:
        return None, errors
    return data, []


def import_calendar_from_legacy_file(
    base_path: Path, *, allow_clobber: bool = False
) -> dict[str, Any]:
    """Import calendar.json into the configured store when empty (or clobber if allowed)."""
    store = get_calendar_store()
    try:
        count = store.item_count()
    except Exception:
        return {
            "status": "failed",
            "error_codes": [CALENDAR_STORE_UNAVAILABLE],
        }

    if count > 0 and not allow_clobber:
        return {
            "status": "refused",
            "error_codes": ["calendar_import_refused_non_empty"],
            "item_count": count,
        }

    calendar, errors = load_legacy_calendar_file(base_path)
    if calendar is None:
        return {"status": "failed", "error_codes": errors}

    force = getattr(store, "force_replace", None)
    if callable(force):
        write_errors = force(calendar)
    else:
        write_errors = store.save(calendar, expected_fingerprint=None)

    if write_errors:
        return {"status": "failed", "error_codes": write_errors}

    return {
        "status": "imported",
        "item_count": len(calendar.get("items", [])),
        "store": store.store_label(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import editorial-calendar/calendar.json into silverman_linkedin_db "
            "(refuses when DB already has items unless --allow-clobber)."
        )
    )
    parser.add_argument(
        "--base-path",
        required=True,
        help="Editorial base path containing editorial-calendar/calendar.json",
    )
    parser.add_argument(
        "--allow-clobber",
        action="store_true",
        help="Overwrite non-empty database (destructive; default refuses)",
    )
    args = parser.parse_args(argv)
    result = import_calendar_from_legacy_file(
        Path(args.base_path), allow_clobber=args.allow_clobber
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "imported" else 1


if __name__ == "__main__":
    sys.exit(main())
