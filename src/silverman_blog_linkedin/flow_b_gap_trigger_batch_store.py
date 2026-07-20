"""Flow B gap-trigger ISO-week batch idempotency store (US-082).

Persists batch records keyed by ``flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}``
in Postgres ``silverman_linkedin_db`` via ``SILVERMAN_CALENDAR_DATABASE_URL``.
Tests use ``memory://``.
"""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Protocol

from silverman_blog_linkedin.editorial_calendar_store import (
    CANONICAL_DATABASE_NAME,
    ENV_CALENDAR_DATABASE_URL,
    MEMORY_URL_PREFIX,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

STATUS_IN_PROGRESS: Literal["in_progress"] = "in_progress"
STATUS_COMPLETED: Literal["completed"] = "completed"
STATUS_FAILED: Literal["failed"] = "failed"

BATCH_STATUSES = frozenset(
    {STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_FAILED}
)

# Crash mid-run must not permanently block the ISO week (design D5).
STALE_IN_PROGRESS_TTL = timedelta(hours=2)

GAP_TRIGGER_BATCH_STORE_NOT_CONFIGURED = "gap_trigger_batch_store_not_configured"
GAP_TRIGGER_BATCH_STORE_UNAVAILABLE = "gap_trigger_batch_store_unavailable"
GAP_TRIGGER_BATCH_CLAIM_DENIED = "gap_trigger_batch_claim_denied"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS flow_b_gap_trigger_batches (
    idempotency_key TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    operator_timezone TEXT NOT NULL,
    iso_week TEXT NOT NULL,
    empty_days JSONB,
    result_summary JSONB,
    error_code TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);
"""


def build_gap_trigger_idempotency_key(operator_timezone: str, iso_week: str) -> str:
    """Build durable ISO-week key ``flow_b_gap_week:{tz}:{YYYY}-W{ww}``."""
    return f"flow_b_gap_week:{operator_timezone}:{iso_week}"


def _parse_utc_iso(value: str) -> datetime | None:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_stale_in_progress(
    record: dict[str, Any],
    *,
    now_utc: datetime,
    ttl: timedelta = STALE_IN_PROGRESS_TTL,
) -> bool:
    if record.get("status") != STATUS_IN_PROGRESS:
        return False
    updated = _parse_utc_iso(str(record.get("updated_at_utc") or ""))
    if updated is None:
        return True
    return now_utc - updated >= ttl


def _row_from_values(
    *,
    idempotency_key: str,
    status: str,
    operator_timezone: str,
    iso_week: str,
    empty_days: list[str] | None,
    result_summary: dict[str, Any] | None,
    error_code: str | None,
    created_at_utc: str,
    updated_at_utc: str,
) -> dict[str, Any]:
    return {
        "idempotency_key": idempotency_key,
        "status": status,
        "operator_timezone": operator_timezone,
        "iso_week": iso_week,
        "empty_days": list(empty_days) if empty_days is not None else None,
        "result_summary": deepcopy(result_summary) if result_summary is not None else None,
        "error_code": error_code,
        "created_at_utc": created_at_utc,
        "updated_at_utc": updated_at_utc,
    }


class GapTriggerBatchStore(Protocol):
    def store_label(self) -> str: ...

    def ensure_schema(self) -> None: ...

    def ping(self) -> bool: ...

    def get(self, idempotency_key: str) -> tuple[dict[str, Any] | None, list[str]]: ...

    def try_claim(
        self,
        *,
        idempotency_key: str,
        operator_timezone: str,
        iso_week: str,
        empty_days: list[str] | None,
        now_utc: datetime | None = None,
    ) -> tuple[dict[str, Any] | None, str | None, list[str]]:
        """Exclusive claim: absent/failed/stale in_progress → in_progress.

        Returns ``(record, denial_reason, errors)``.
        ``denial_reason`` is ``in_progress`` or ``completed`` when blocked.
        """
        ...

    def mark_completed(
        self,
        idempotency_key: str,
        *,
        result_summary: dict[str, Any] | None = None,
        empty_days: list[str] | None = None,
    ) -> list[str]: ...

    def mark_failed(
        self,
        idempotency_key: str,
        *,
        error_code: str,
        result_summary: dict[str, Any] | None = None,
    ) -> list[str]: ...


class MemoryGapTriggerBatchStore:
    """Process-local store for unit tests (``SILVERMAN_CALENDAR_DATABASE_URL=memory://``)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rows: dict[str, dict[str, Any]] = {}

    def store_label(self) -> str:
        return "memory:test"

    def ensure_schema(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def get(self, idempotency_key: str) -> tuple[dict[str, Any] | None, list[str]]:
        with self._lock:
            row = self._rows.get(idempotency_key)
            if row is None:
                return None, []
            return deepcopy(row), []

    def try_claim(
        self,
        *,
        idempotency_key: str,
        operator_timezone: str,
        iso_week: str,
        empty_days: list[str] | None,
        now_utc: datetime | None = None,
    ) -> tuple[dict[str, Any] | None, str | None, list[str]]:
        clock = now_utc or datetime.now(timezone.utc)
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        else:
            clock = clock.astimezone(timezone.utc)
        stamp = clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._lock:
            existing = self._rows.get(idempotency_key)
            if existing is not None:
                status = str(existing.get("status") or "")
                if status == STATUS_COMPLETED:
                    return deepcopy(existing), STATUS_COMPLETED, []
                if status == STATUS_IN_PROGRESS and not _is_stale_in_progress(
                    existing, now_utc=clock
                ):
                    return deepcopy(existing), STATUS_IN_PROGRESS, []
                # failed or stale in_progress → reclaim
            created = (
                str(existing["created_at_utc"])
                if existing is not None
                else stamp
            )
            row = _row_from_values(
                idempotency_key=idempotency_key,
                status=STATUS_IN_PROGRESS,
                operator_timezone=operator_timezone,
                iso_week=iso_week,
                empty_days=empty_days,
                result_summary=None,
                error_code=None,
                created_at_utc=created,
                updated_at_utc=stamp,
            )
            self._rows[idempotency_key] = row
            return deepcopy(row), None, []

    def mark_completed(
        self,
        idempotency_key: str,
        *,
        result_summary: dict[str, Any] | None = None,
        empty_days: list[str] | None = None,
    ) -> list[str]:
        stamp = utc_now_iso()
        with self._lock:
            existing = self._rows.get(idempotency_key)
            if existing is None:
                return [GAP_TRIGGER_BATCH_CLAIM_DENIED]
            updated = deepcopy(existing)
            updated["status"] = STATUS_COMPLETED
            updated["updated_at_utc"] = stamp
            updated["error_code"] = None
            if result_summary is not None:
                updated["result_summary"] = deepcopy(result_summary)
            if empty_days is not None:
                updated["empty_days"] = list(empty_days)
            self._rows[idempotency_key] = updated
        return []

    def mark_failed(
        self,
        idempotency_key: str,
        *,
        error_code: str,
        result_summary: dict[str, Any] | None = None,
    ) -> list[str]:
        stamp = utc_now_iso()
        with self._lock:
            existing = self._rows.get(idempotency_key)
            if existing is None:
                return [GAP_TRIGGER_BATCH_CLAIM_DENIED]
            updated = deepcopy(existing)
            updated["status"] = STATUS_FAILED
            updated["updated_at_utc"] = stamp
            updated["error_code"] = error_code
            if result_summary is not None:
                updated["result_summary"] = deepcopy(result_summary)
            self._rows[idempotency_key] = updated
        return []

    def clear(self) -> None:
        """Test helper: remove all batch rows."""
        with self._lock:
            self._rows.clear()

    def force_set(self, record: dict[str, Any]) -> None:
        """Test helper: insert/replace a row without claim semantics."""
        with self._lock:
            self._rows[str(record["idempotency_key"])] = deepcopy(record)


class PostgresGapTriggerBatchStore:
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

    @staticmethod
    def _decode_row(row: tuple[Any, ...]) -> dict[str, Any]:
        empty_days = row[4]
        result_summary = row[5]
        if isinstance(empty_days, str):
            empty_days = json.loads(empty_days)
        if isinstance(result_summary, str):
            result_summary = json.loads(result_summary)
        return _row_from_values(
            idempotency_key=str(row[0]),
            status=str(row[1]),
            operator_timezone=str(row[2]),
            iso_week=str(row[3]),
            empty_days=list(empty_days) if empty_days is not None else None,
            result_summary=(
                dict(result_summary) if isinstance(result_summary, dict) else None
            ),
            error_code=str(row[6]) if row[6] is not None else None,
            created_at_utc=str(row[7]),
            updated_at_utc=str(row[8]),
        )

    def get(self, idempotency_key: str) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            idempotency_key,
                            status,
                            operator_timezone,
                            iso_week,
                            empty_days,
                            result_summary,
                            error_code,
                            created_at_utc,
                            updated_at_utc
                        FROM flow_b_gap_trigger_batches
                        WHERE idempotency_key = %s
                        """,
                        (idempotency_key,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None, []
                    return self._decode_row(row), []
        except Exception:
            return None, [GAP_TRIGGER_BATCH_STORE_UNAVAILABLE]

    def try_claim(
        self,
        *,
        idempotency_key: str,
        operator_timezone: str,
        iso_week: str,
        empty_days: list[str] | None,
        now_utc: datetime | None = None,
    ) -> tuple[dict[str, Any] | None, str | None, list[str]]:
        clock = now_utc or datetime.now(timezone.utc)
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        else:
            clock = clock.astimezone(timezone.utc)
        stamp = clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        empty_json = json.dumps(list(empty_days) if empty_days is not None else [])
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            idempotency_key,
                            status,
                            operator_timezone,
                            iso_week,
                            empty_days,
                            result_summary,
                            error_code,
                            created_at_utc,
                            updated_at_utc
                        FROM flow_b_gap_trigger_batches
                        WHERE idempotency_key = %s
                        FOR UPDATE
                        """,
                        (idempotency_key,),
                    )
                    existing_row = cur.fetchone()
                    if existing_row is not None:
                        existing = self._decode_row(existing_row)
                        status = existing["status"]
                        if status == STATUS_COMPLETED:
                            return existing, STATUS_COMPLETED, []
                        if status == STATUS_IN_PROGRESS and not _is_stale_in_progress(
                            existing, now_utc=clock
                        ):
                            return existing, STATUS_IN_PROGRESS, []
                        created = existing["created_at_utc"]
                        cur.execute(
                            """
                            UPDATE flow_b_gap_trigger_batches SET
                                status = %s,
                                operator_timezone = %s,
                                iso_week = %s,
                                empty_days = %s::jsonb,
                                result_summary = NULL,
                                error_code = NULL,
                                updated_at_utc = %s
                            WHERE idempotency_key = %s
                            """,
                            (
                                STATUS_IN_PROGRESS,
                                operator_timezone,
                                iso_week,
                                empty_json,
                                stamp,
                                idempotency_key,
                            ),
                        )
                    else:
                        created = stamp
                        cur.execute(
                            """
                            INSERT INTO flow_b_gap_trigger_batches (
                                idempotency_key,
                                status,
                                operator_timezone,
                                iso_week,
                                empty_days,
                                result_summary,
                                error_code,
                                created_at_utc,
                                updated_at_utc
                            ) VALUES (
                                %s, %s, %s, %s, %s::jsonb, NULL, NULL, %s, %s
                            )
                            """,
                            (
                                idempotency_key,
                                STATUS_IN_PROGRESS,
                                operator_timezone,
                                iso_week,
                                empty_json,
                                created,
                                stamp,
                            ),
                        )
                conn.commit()
            claimed = _row_from_values(
                idempotency_key=idempotency_key,
                status=STATUS_IN_PROGRESS,
                operator_timezone=operator_timezone,
                iso_week=iso_week,
                empty_days=empty_days,
                result_summary=None,
                error_code=None,
                created_at_utc=created,
                updated_at_utc=stamp,
            )
            return claimed, None, []
        except Exception:
            return None, None, [GAP_TRIGGER_BATCH_STORE_UNAVAILABLE]

    def mark_completed(
        self,
        idempotency_key: str,
        *,
        result_summary: dict[str, Any] | None = None,
        empty_days: list[str] | None = None,
    ) -> list[str]:
        stamp = utc_now_iso()
        summary_json = (
            json.dumps(result_summary) if result_summary is not None else None
        )
        empty_json = (
            json.dumps(list(empty_days)) if empty_days is not None else None
        )
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    if empty_json is not None:
                        cur.execute(
                            """
                            UPDATE flow_b_gap_trigger_batches SET
                                status = %s,
                                result_summary = %s::jsonb,
                                empty_days = %s::jsonb,
                                error_code = NULL,
                                updated_at_utc = %s
                            WHERE idempotency_key = %s
                            """,
                            (
                                STATUS_COMPLETED,
                                summary_json,
                                empty_json,
                                stamp,
                                idempotency_key,
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE flow_b_gap_trigger_batches SET
                                status = %s,
                                result_summary = %s::jsonb,
                                error_code = NULL,
                                updated_at_utc = %s
                            WHERE idempotency_key = %s
                            """,
                            (
                                STATUS_COMPLETED,
                                summary_json,
                                stamp,
                                idempotency_key,
                            ),
                        )
                    if cur.rowcount == 0:
                        return [GAP_TRIGGER_BATCH_CLAIM_DENIED]
                conn.commit()
            return []
        except Exception:
            return [GAP_TRIGGER_BATCH_STORE_UNAVAILABLE]

    def mark_failed(
        self,
        idempotency_key: str,
        *,
        error_code: str,
        result_summary: dict[str, Any] | None = None,
    ) -> list[str]:
        stamp = utc_now_iso()
        summary_json = (
            json.dumps(result_summary) if result_summary is not None else None
        )
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE flow_b_gap_trigger_batches SET
                            status = %s,
                            error_code = %s,
                            result_summary = %s::jsonb,
                            updated_at_utc = %s
                        WHERE idempotency_key = %s
                        """,
                        (
                            STATUS_FAILED,
                            error_code,
                            summary_json,
                            stamp,
                            idempotency_key,
                        ),
                    )
                    if cur.rowcount == 0:
                        return [GAP_TRIGGER_BATCH_CLAIM_DENIED]
                conn.commit()
            return []
        except Exception:
            return [GAP_TRIGGER_BATCH_STORE_UNAVAILABLE]


_store_lock = threading.RLock()
_store: GapTriggerBatchStore | None = None


def reset_gap_trigger_batch_store_for_tests(
    store: GapTriggerBatchStore | None = None,
) -> None:
    """Replace the process gap-trigger batch store (tests only)."""
    global _store
    with _store_lock:
        _store = store


def create_gap_trigger_batch_store_from_url(database_url: str) -> GapTriggerBatchStore:
    stripped = database_url.strip()
    if not stripped:
        raise ValueError(GAP_TRIGGER_BATCH_STORE_NOT_CONFIGURED)
    if stripped.startswith(MEMORY_URL_PREFIX):
        return MemoryGapTriggerBatchStore()
    return PostgresGapTriggerBatchStore(stripped)


def get_gap_trigger_batch_store() -> GapTriggerBatchStore:
    """Return the configured batch store (lazy singleton; same URL as calendar)."""
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        raw = os.environ.get(ENV_CALENDAR_DATABASE_URL, "").strip()
        if not raw:
            raise RuntimeError(GAP_TRIGGER_BATCH_STORE_NOT_CONFIGURED)
        _store = create_gap_trigger_batch_store_from_url(raw)
        return _store
