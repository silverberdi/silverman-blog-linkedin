"""Flow B gap operator settings: defaults, validation, load/save helpers (US-076).

Postgres-backed SoT via ``flow_b_gap_operator_settings_store``. Documented defaults
apply when no row exists. Saving settings MUST NOT enable LinkedIn API publish.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from silverman_blog_linkedin.flow_b_gap_operator_settings_store import (
    DEFAULT_SETTINGS_ID,
    GapOperatorSettingsStore,
    get_gap_operator_settings_store,
)
from silverman_blog_linkedin.local_day_density import ENV_OPERATOR_TIMEZONE
from silverman_blog_linkedin.run_metadata import utc_now_iso

GAP_SCAN_MODE_NEXT_WEEK = "next_week"
ALLOWED_GAP_SCAN_MODES = frozenset({GAP_SCAN_MODE_NEXT_WEEK})

WEEKDAY_MONDAY = "monday"
WEEKDAY_TUESDAY = "tuesday"
WEEKDAY_WEDNESDAY = "wednesday"
WEEKDAY_THURSDAY = "thursday"
WEEKDAY_FRIDAY = "friday"
WEEKDAY_SATURDAY = "saturday"
WEEKDAY_SUNDAY = "sunday"
ALLOWED_WEEKDAYS = frozenset(
    {
        WEEKDAY_MONDAY,
        WEEKDAY_TUESDAY,
        WEEKDAY_WEDNESDAY,
        WEEKDAY_THURSDAY,
        WEEKDAY_FRIDAY,
        WEEKDAY_SATURDAY,
        WEEKDAY_SUNDAY,
    }
)

# Documented placeholder when no row and SILVERMAN_OPERATOR_TIMEZONE is unset/invalid.
DEFAULT_OPERATOR_TIMEZONE_PLACEHOLDER = "UTC"

DEFAULT_GAP_TRIGGER_ENABLED = False
DEFAULT_GAP_SCAN_MODE = GAP_SCAN_MODE_NEXT_WEEK
DEFAULT_WEEKLY_RUN_LOCAL_DAY = WEEKDAY_FRIDAY
DEFAULT_WEEKLY_RUN_LOCAL_TIME = "15:00"
DEFAULT_MIN_LEAD_DAYS = 5
DEFAULT_GAP_POSTS_THRESHOLD = 0
DEFAULT_MAX_DRAFTS_PER_WEEKLY_RUN = 2
DEFAULT_DENSITY_MAX_PER_LOCAL_DAY = 2

SOURCE_DEFAULTS: Literal["defaults"] = "defaults"
SOURCE_DATABASE: Literal["database"] = "database"

SETTINGS_KEY_OPERATOR_TIMEZONE = "operator_timezone"
SETTINGS_KEY_GAP_TRIGGER_ENABLED = "gap_trigger_enabled"
SETTINGS_KEY_GAP_SCAN_MODE = "gap_scan_mode"
SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY = "weekly_run_local_day"
SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME = "weekly_run_local_time"
SETTINGS_KEY_MIN_LEAD_DAYS = "min_lead_days"
SETTINGS_KEY_GAP_POSTS_THRESHOLD = "gap_posts_threshold"
SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN = "max_drafts_per_weekly_run"
SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY = "density_max_per_local_day"

KNOWN_SETTINGS_KEYS = frozenset(
    {
        SETTINGS_KEY_OPERATOR_TIMEZONE,
        SETTINGS_KEY_GAP_TRIGGER_ENABLED,
        SETTINGS_KEY_GAP_SCAN_MODE,
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY,
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME,
        SETTINGS_KEY_MIN_LEAD_DAYS,
        SETTINGS_KEY_GAP_POSTS_THRESHOLD,
        SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN,
        SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY,
    }
)

ERROR_OPERATOR_TIMEZONE_INVALID = "operator_timezone_invalid"
ERROR_WEEKLY_RUN_LOCAL_TIME_INVALID = "weekly_run_local_time_invalid"
ERROR_WEEKLY_RUN_LOCAL_DAY_INVALID = "weekly_run_local_day_invalid"
ERROR_GAP_SCAN_MODE_INVALID = "gap_scan_mode_invalid"
ERROR_GAP_TRIGGER_ENABLED_INVALID = "gap_trigger_enabled_invalid"
ERROR_MIN_LEAD_DAYS_INVALID = "min_lead_days_invalid"
ERROR_GAP_POSTS_THRESHOLD_INVALID = "gap_posts_threshold_invalid"
ERROR_MAX_DRAFTS_PER_WEEKLY_RUN_INVALID = "max_drafts_per_weekly_run_invalid"
ERROR_DENSITY_MAX_PER_LOCAL_DAY_INVALID = "density_max_per_local_day_invalid"
ERROR_EXPECTED_ROW_VERSION_CONFLICT = "gap_operator_settings_concurrent_update"
ERROR_SETTINGS_STORE_UNAVAILABLE = "gap_operator_settings_store_unavailable"
ERROR_SETTINGS_STORE_NOT_CONFIGURED = "gap_operator_settings_store_not_configured"

_HH_MM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _env_operator_timezone_if_valid(
    environ: dict[str, str] | None = None,
) -> str | None:
    env = os.environ if environ is None else environ
    raw = env.get(ENV_OPERATOR_TIMEZONE)
    if not isinstance(raw, str) or not raw.strip():
        return None
    name = raw.strip()
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return None
    return name


def default_operator_timezone(*, environ: dict[str, str] | None = None) -> str:
    """Effective default timezone when no settings row exists."""
    from_env = _env_operator_timezone_if_valid(environ)
    if from_env is not None:
        return from_env
    return DEFAULT_OPERATOR_TIMEZONE_PLACEHOLDER


def documented_defaults(*, environ: dict[str, str] | None = None) -> dict[str, Any]:
    """Return the full documented defaults document (no metadata)."""
    return {
        SETTINGS_KEY_OPERATOR_TIMEZONE: default_operator_timezone(environ=environ),
        SETTINGS_KEY_GAP_TRIGGER_ENABLED: DEFAULT_GAP_TRIGGER_ENABLED,
        SETTINGS_KEY_GAP_SCAN_MODE: DEFAULT_GAP_SCAN_MODE,
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY: DEFAULT_WEEKLY_RUN_LOCAL_DAY,
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME: DEFAULT_WEEKLY_RUN_LOCAL_TIME,
        SETTINGS_KEY_MIN_LEAD_DAYS: DEFAULT_MIN_LEAD_DAYS,
        SETTINGS_KEY_GAP_POSTS_THRESHOLD: DEFAULT_GAP_POSTS_THRESHOLD,
        SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN: DEFAULT_MAX_DRAFTS_PER_WEEKLY_RUN,
        SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY: DEFAULT_DENSITY_MAX_PER_LOCAL_DAY,
    }


def is_valid_iana_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError, KeyError):
        return False
    return True


def is_valid_hh_mm(value: str) -> bool:
    return bool(_HH_MM_RE.fullmatch(value))


def validate_gap_operator_settings_document(
    document: dict[str, Any],
) -> list[dict[str, str]]:
    """Validate a settings document. Returns structured errors (code + field).

    Invalid writes MUST NOT partially persist — callers check this before save.
    """
    errors: list[dict[str, str]] = []

    tz = document.get(SETTINGS_KEY_OPERATOR_TIMEZONE)
    if not isinstance(tz, str) or not tz.strip() or not is_valid_iana_timezone(tz.strip()):
        errors.append(
            {
                "field": SETTINGS_KEY_OPERATOR_TIMEZONE,
                "code": ERROR_OPERATOR_TIMEZONE_INVALID,
                "message": "operator_timezone must be a valid IANA timezone",
            }
        )

    enabled = document.get(SETTINGS_KEY_GAP_TRIGGER_ENABLED)
    if not isinstance(enabled, bool):
        errors.append(
            {
                "field": SETTINGS_KEY_GAP_TRIGGER_ENABLED,
                "code": ERROR_GAP_TRIGGER_ENABLED_INVALID,
                "message": "gap_trigger_enabled must be a boolean",
            }
        )

    scan_mode = document.get(SETTINGS_KEY_GAP_SCAN_MODE)
    if not isinstance(scan_mode, str) or scan_mode not in ALLOWED_GAP_SCAN_MODES:
        errors.append(
            {
                "field": SETTINGS_KEY_GAP_SCAN_MODE,
                "code": ERROR_GAP_SCAN_MODE_INVALID,
                "message": "gap_scan_mode must be one of: next_week",
            }
        )

    day = document.get(SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY)
    if not isinstance(day, str) or day not in ALLOWED_WEEKDAYS:
        errors.append(
            {
                "field": SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY,
                "code": ERROR_WEEKLY_RUN_LOCAL_DAY_INVALID,
                "message": "weekly_run_local_day must be a lowercase weekday (monday–sunday)",
            }
        )

    time_of_day = document.get(SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME)
    if not isinstance(time_of_day, str) or not is_valid_hh_mm(time_of_day):
        errors.append(
            {
                "field": SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME,
                "code": ERROR_WEEKLY_RUN_LOCAL_TIME_INVALID,
                "message": "weekly_run_local_time must be HH:MM in 24-hour form",
            }
        )

    for key, code in (
        (SETTINGS_KEY_MIN_LEAD_DAYS, ERROR_MIN_LEAD_DAYS_INVALID),
        (SETTINGS_KEY_GAP_POSTS_THRESHOLD, ERROR_GAP_POSTS_THRESHOLD_INVALID),
        (SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN, ERROR_MAX_DRAFTS_PER_WEEKLY_RUN_INVALID),
        (SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY, ERROR_DENSITY_MAX_PER_LOCAL_DAY_INVALID),
    ):
        value = document.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(
                {
                    "field": key,
                    "code": code,
                    "message": f"{key} must be a non-negative integer",
                }
            )

    return errors


def normalize_settings_document(document: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized known-keys document (timezone stripped)."""
    tz = document[SETTINGS_KEY_OPERATOR_TIMEZONE]
    assert isinstance(tz, str)
    return {
        SETTINGS_KEY_OPERATOR_TIMEZONE: tz.strip(),
        SETTINGS_KEY_GAP_TRIGGER_ENABLED: bool(
            document[SETTINGS_KEY_GAP_TRIGGER_ENABLED]
        ),
        SETTINGS_KEY_GAP_SCAN_MODE: document[SETTINGS_KEY_GAP_SCAN_MODE],
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY: document[SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY],
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME: document[SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME],
        SETTINGS_KEY_MIN_LEAD_DAYS: int(document[SETTINGS_KEY_MIN_LEAD_DAYS]),
        SETTINGS_KEY_GAP_POSTS_THRESHOLD: int(document[SETTINGS_KEY_GAP_POSTS_THRESHOLD]),
        SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN: int(
            document[SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN]
        ),
        SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY: int(
            document[SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY]
        ),
    }


@dataclass(frozen=True)
class GapOperatorSettingsSnapshot:
    """Effective settings plus read metadata."""

    settings: dict[str, Any]
    source: Literal["defaults", "database"]
    updated_at_utc: str | None
    row_version: int | None
    settings_id: str = DEFAULT_SETTINGS_ID

    def to_response_dict(self) -> dict[str, Any]:
        """Secret-safe HTTP response body (settings keys + metadata only)."""
        return {
            "settings_id": self.settings_id,
            "source": self.source,
            "updated_at_utc": self.updated_at_utc,
            "row_version": self.row_version,
            **self.settings,
        }


def load_gap_operator_settings(
    *,
    store: GapOperatorSettingsStore | None = None,
    environ: dict[str, str] | None = None,
) -> GapOperatorSettingsSnapshot:
    """Load effective settings: DB row when present, otherwise documented defaults."""
    active = store if store is not None else get_gap_operator_settings_store()
    row, errors = active.load()
    if errors:
        # Unreachable/misconfigured store: fail closed by raising for callers that need live DB.
        # For unit tests memory store never returns load errors.
        raise RuntimeError(errors[0] if errors else ERROR_SETTINGS_STORE_UNAVAILABLE)
    if row is None:
        return GapOperatorSettingsSnapshot(
            settings=documented_defaults(environ=environ),
            source=SOURCE_DEFAULTS,
            updated_at_utc=None,
            row_version=None,
        )
    settings = {
        SETTINGS_KEY_OPERATOR_TIMEZONE: row[SETTINGS_KEY_OPERATOR_TIMEZONE],
        SETTINGS_KEY_GAP_TRIGGER_ENABLED: row[SETTINGS_KEY_GAP_TRIGGER_ENABLED],
        SETTINGS_KEY_GAP_SCAN_MODE: row[SETTINGS_KEY_GAP_SCAN_MODE],
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY: row[SETTINGS_KEY_WEEKLY_RUN_LOCAL_DAY],
        SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME: row[SETTINGS_KEY_WEEKLY_RUN_LOCAL_TIME],
        SETTINGS_KEY_MIN_LEAD_DAYS: row[SETTINGS_KEY_MIN_LEAD_DAYS],
        SETTINGS_KEY_GAP_POSTS_THRESHOLD: row[SETTINGS_KEY_GAP_POSTS_THRESHOLD],
        SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN: row[
            SETTINGS_KEY_MAX_DRAFTS_PER_WEEKLY_RUN
        ],
        SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY: row[
            SETTINGS_KEY_DENSITY_MAX_PER_LOCAL_DAY
        ],
    }
    return GapOperatorSettingsSnapshot(
        settings=settings,
        source=SOURCE_DATABASE,
        updated_at_utc=row.get("updated_at_utc"),
        row_version=row.get("row_version"),
    )


def save_gap_operator_settings(
    document: dict[str, Any],
    *,
    expected_row_version: int | None = None,
    store: GapOperatorSettingsStore | None = None,
) -> tuple[GapOperatorSettingsSnapshot | None, list[dict[str, str]]]:
    """Validate and persist a full settings document.

    Returns ``(snapshot, [])`` on success or ``(None, errors)`` on validation /
    concurrency / store failure. Does not mutate LinkedIn publish enablement.
    """
    validation_errors = validate_gap_operator_settings_document(document)
    if validation_errors:
        return None, validation_errors

    normalized = normalize_settings_document(document)
    payload = {
        **normalized,
        "updated_at_utc": utc_now_iso(),
    }
    active = store if store is not None else get_gap_operator_settings_store()
    save_errors = active.save(payload, expected_row_version=expected_row_version)
    if save_errors:
        structured: list[dict[str, str]] = []
        for code in save_errors:
            if code == ERROR_EXPECTED_ROW_VERSION_CONFLICT:
                structured.append(
                    {
                        "field": "row_version",
                        "code": code,
                        "message": "settings were updated concurrently; reload and retry",
                    }
                )
            else:
                structured.append(
                    {
                        "field": "_store",
                        "code": code,
                        "message": "settings store write failed",
                    }
                )
        return None, structured

    return load_gap_operator_settings(store=active), []
