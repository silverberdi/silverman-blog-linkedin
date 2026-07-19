"""Flow B gap operator settings store (Postgres ``silverman_linkedin_db`` or memory).

Reuses ``SILVERMAN_CALENDAR_DATABASE_URL`` targeting the same database as the
editorial calendar (US-041). Tests use ``memory://``.
"""

from __future__ import annotations

import os
import threading
from copy import deepcopy
from typing import Any, Protocol

from silverman_blog_linkedin.editorial_calendar_store import (
    CANONICAL_DATABASE_NAME,
    ENV_CALENDAR_DATABASE_URL,
    MEMORY_URL_PREFIX,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

DEFAULT_SETTINGS_ID = "default"

GAP_SETTINGS_STORE_NOT_CONFIGURED = "gap_operator_settings_store_not_configured"
GAP_SETTINGS_STORE_UNAVAILABLE = "gap_operator_settings_store_unavailable"
GAP_SETTINGS_CONCURRENT_UPDATE = "gap_operator_settings_concurrent_update"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS flow_b_gap_operator_settings (
    settings_id TEXT PRIMARY KEY,
    operator_timezone TEXT NOT NULL,
    gap_trigger_enabled BOOLEAN NOT NULL,
    gap_scan_mode TEXT NOT NULL,
    weekly_run_local_day TEXT NOT NULL,
    weekly_run_local_time TEXT NOT NULL,
    min_lead_days INTEGER NOT NULL,
    gap_posts_threshold INTEGER NOT NULL,
    max_drafts_per_weekly_run INTEGER NOT NULL,
    density_max_per_local_day INTEGER NOT NULL,
    updated_at_utc TEXT NOT NULL,
    row_version BIGINT NOT NULL DEFAULT 0
);
"""

_SETTING_COLUMNS = (
    "operator_timezone",
    "gap_trigger_enabled",
    "gap_scan_mode",
    "weekly_run_local_day",
    "weekly_run_local_time",
    "min_lead_days",
    "gap_posts_threshold",
    "max_drafts_per_weekly_run",
    "density_max_per_local_day",
    "updated_at_utc",
    "row_version",
)


class GapOperatorSettingsStore(Protocol):
    def store_label(self) -> str: ...

    def ensure_schema(self) -> None: ...

    def ping(self) -> bool: ...

    def load(self) -> tuple[dict[str, Any] | None, list[str]]: ...

    def save(
        self,
        document: dict[str, Any],
        *,
        expected_row_version: int | None,
    ) -> list[str]: ...


class MemoryGapOperatorSettingsStore:
    """Process-local store for unit tests (``SILVERMAN_CALENDAR_DATABASE_URL=memory://``)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._row: dict[str, Any] | None = None

    def store_label(self) -> str:
        return "memory:test"

    def ensure_schema(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def load(self) -> tuple[dict[str, Any] | None, list[str]]:
        with self._lock:
            if self._row is None:
                return None, []
            return deepcopy(self._row), []

    def save(
        self,
        document: dict[str, Any],
        *,
        expected_row_version: int | None,
    ) -> list[str]:
        payload = deepcopy(document)
        payload.setdefault("updated_at_utc", utc_now_iso())
        with self._lock:
            current_version = (
                int(self._row["row_version"]) if self._row is not None else None
            )
            if expected_row_version is not None:
                if current_version is None and expected_row_version != 0:
                    return [GAP_SETTINGS_CONCURRENT_UPDATE]
                if (
                    current_version is not None
                    and expected_row_version != current_version
                ):
                    return [GAP_SETTINGS_CONCURRENT_UPDATE]
            next_version = 1 if current_version is None else current_version + 1
            self._row = {
                "settings_id": DEFAULT_SETTINGS_ID,
                **{k: payload[k] for k in _SETTING_COLUMNS if k != "row_version"},
                "row_version": next_version,
            }
        return []

    def clear(self) -> None:
        """Test helper: remove the singleton row."""
        with self._lock:
            self._row = None


class PostgresGapOperatorSettingsStore:
    """PostgreSQL store targeting database ``silverman_linkedin_db``."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_url_targets_canonical_db(database_url)

    @staticmethod
    def _ensure_url_targets_canonical_db(database_url: str) -> None:
        path = database_url.rsplit("/", 1)[-1]
        db_name = path.split("?", 1)[0]
        if db_name != CANONICAL_DATABASE_NAME:
            raise ValueError(
                f"{ENV_CALENDAR_DATABASE_URL} must target database "
                f"{CANONICAL_DATABASE_NAME!r}, got {db_name!r}"
            )

    def store_label(self) -> str:
        return f"postgres:{CANONICAL_DATABASE_NAME}"

    def _connect(self):
        import psycopg

        return psycopg.connect(self._database_url)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            conn.commit()

    def ping(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception:
            return False

    def load(self) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            operator_timezone,
                            gap_trigger_enabled,
                            gap_scan_mode,
                            weekly_run_local_day,
                            weekly_run_local_time,
                            min_lead_days,
                            gap_posts_threshold,
                            max_drafts_per_weekly_run,
                            density_max_per_local_day,
                            updated_at_utc,
                            row_version
                        FROM flow_b_gap_operator_settings
                        WHERE settings_id = %s
                        """,
                        (DEFAULT_SETTINGS_ID,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None, []
                    return (
                        {
                            "settings_id": DEFAULT_SETTINGS_ID,
                            "operator_timezone": row[0],
                            "gap_trigger_enabled": bool(row[1]),
                            "gap_scan_mode": row[2],
                            "weekly_run_local_day": row[3],
                            "weekly_run_local_time": row[4],
                            "min_lead_days": int(row[5]),
                            "gap_posts_threshold": int(row[6]),
                            "max_drafts_per_weekly_run": int(row[7]),
                            "density_max_per_local_day": int(row[8]),
                            "updated_at_utc": row[9],
                            "row_version": int(row[10]),
                        },
                        [],
                    )
        except Exception:
            return None, [GAP_SETTINGS_STORE_UNAVAILABLE]

    def save(
        self,
        document: dict[str, Any],
        *,
        expected_row_version: int | None,
    ) -> list[str]:
        try:
            self.ensure_schema()
            payload = deepcopy(document)
            payload.setdefault("updated_at_utc", utc_now_iso())
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT row_version
                        FROM flow_b_gap_operator_settings
                        WHERE settings_id = %s
                        FOR UPDATE
                        """,
                        (DEFAULT_SETTINGS_ID,),
                    )
                    existing = cur.fetchone()
                    current_version = int(existing[0]) if existing else None
                    if expected_row_version is not None:
                        if current_version is None and expected_row_version != 0:
                            return [GAP_SETTINGS_CONCURRENT_UPDATE]
                        if (
                            current_version is not None
                            and expected_row_version != current_version
                        ):
                            return [GAP_SETTINGS_CONCURRENT_UPDATE]
                    next_version = (
                        1 if current_version is None else current_version + 1
                    )
                    cur.execute(
                        """
                        INSERT INTO flow_b_gap_operator_settings (
                            settings_id,
                            operator_timezone,
                            gap_trigger_enabled,
                            gap_scan_mode,
                            weekly_run_local_day,
                            weekly_run_local_time,
                            min_lead_days,
                            gap_posts_threshold,
                            max_drafts_per_weekly_run,
                            density_max_per_local_day,
                            updated_at_utc,
                            row_version
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (settings_id) DO UPDATE SET
                            operator_timezone = EXCLUDED.operator_timezone,
                            gap_trigger_enabled = EXCLUDED.gap_trigger_enabled,
                            gap_scan_mode = EXCLUDED.gap_scan_mode,
                            weekly_run_local_day = EXCLUDED.weekly_run_local_day,
                            weekly_run_local_time = EXCLUDED.weekly_run_local_time,
                            min_lead_days = EXCLUDED.min_lead_days,
                            gap_posts_threshold = EXCLUDED.gap_posts_threshold,
                            max_drafts_per_weekly_run = EXCLUDED.max_drafts_per_weekly_run,
                            density_max_per_local_day = EXCLUDED.density_max_per_local_day,
                            updated_at_utc = EXCLUDED.updated_at_utc,
                            row_version = EXCLUDED.row_version
                        """,
                        (
                            DEFAULT_SETTINGS_ID,
                            payload["operator_timezone"],
                            payload["gap_trigger_enabled"],
                            payload["gap_scan_mode"],
                            payload["weekly_run_local_day"],
                            payload["weekly_run_local_time"],
                            payload["min_lead_days"],
                            payload["gap_posts_threshold"],
                            payload["max_drafts_per_weekly_run"],
                            payload["density_max_per_local_day"],
                            payload["updated_at_utc"],
                            next_version,
                        ),
                    )
                conn.commit()
            return []
        except Exception:
            return [GAP_SETTINGS_STORE_UNAVAILABLE]


_store_lock = threading.RLock()
_store: GapOperatorSettingsStore | None = None


def reset_gap_operator_settings_store_for_tests(
    store: GapOperatorSettingsStore | None = None,
) -> None:
    """Replace the process gap-settings store (tests only)."""
    global _store
    with _store_lock:
        _store = store


def create_gap_operator_settings_store_from_url(
    database_url: str,
) -> GapOperatorSettingsStore:
    stripped = database_url.strip()
    if not stripped:
        raise ValueError(GAP_SETTINGS_STORE_NOT_CONFIGURED)
    if stripped.startswith(MEMORY_URL_PREFIX):
        return MemoryGapOperatorSettingsStore()
    return PostgresGapOperatorSettingsStore(stripped)


def get_gap_operator_settings_store() -> GapOperatorSettingsStore:
    """Return the configured settings store (lazy singleton; same URL as calendar)."""
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        raw = os.environ.get(ENV_CALENDAR_DATABASE_URL, "").strip()
        if not raw:
            raise RuntimeError(GAP_SETTINGS_STORE_NOT_CONFIGURED)
        _store = create_gap_operator_settings_store_from_url(raw)
        return _store
