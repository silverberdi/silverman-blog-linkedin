"""Editorial calendar persistence store (Postgres `silverman_linkedin_db` or memory for tests)."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from silverman_blog_linkedin.run_metadata import utc_now_iso

ENV_CALENDAR_DATABASE_URL = "SILVERMAN_CALENDAR_DATABASE_URL"
CANONICAL_DATABASE_NAME = "silverman_linkedin_db"
MEMORY_URL_PREFIX = "memory://"
MASTER_CALENDAR_ID = "master"

CALENDAR_STORE_NOT_CONFIGURED = "calendar_store_not_configured"
CALENDAR_STORE_UNAVAILABLE = "calendar_store_unavailable"
CALENDAR_STORE_SCHEMA_INVALID = "calendar_store_schema_invalid"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS editorial_calendar (
    calendar_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    row_version BIGINT NOT NULL DEFAULT 0,
    content_sha256 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS editorial_calendar_items (
    calendar_id TEXT NOT NULL REFERENCES editorial_calendar (calendar_id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (calendar_id, item_id)
);
"""


def canonical_calendar_digest(calendar: dict[str, Any]) -> str:
    """Return SHA-256 hex digest of a stable calendar encoding (API fingerprint)."""
    payload = {
        "schema_version": calendar.get("schema_version"),
        "updated_at_utc": calendar.get("updated_at_utc"),
        "items": calendar.get("items", []),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def empty_calendar_document(*, updated_at_utc: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "updated_at_utc": updated_at_utc or utc_now_iso(),
        "items": [],
    }


class CalendarStore(Protocol):
    def store_label(self) -> str: ...

    def ensure_schema(self) -> None: ...

    def ping(self) -> bool: ...

    def load(self) -> tuple[dict[str, Any] | None, list[str]]: ...

    def save(
        self,
        calendar: dict[str, Any],
        *,
        expected_fingerprint: str | None,
    ) -> list[str]: ...

    def item_count(self) -> int: ...


@dataclass
class _MemoryState:
    document: dict[str, Any]
    row_version: int
    content_sha256: str


class MemoryCalendarStore:
    """Process-local store for unit tests (`SILVERMAN_CALENDAR_DATABASE_URL=memory://`)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        now = utc_now_iso()
        empty = empty_calendar_document(updated_at_utc=now)
        self._state = _MemoryState(
            document=empty,
            row_version=0,
            content_sha256=canonical_calendar_digest(empty),
        )

    def store_label(self) -> str:
        return "memory:test"

    def ensure_schema(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def load(self) -> tuple[dict[str, Any] | None, list[str]]:
        with self._lock:
            return deepcopy(self._state.document), []

    def save(
        self,
        calendar: dict[str, Any],
        *,
        expected_fingerprint: str | None,
    ) -> list[str]:
        from silverman_blog_linkedin.editorial_calendar_plan import (
            CALENDAR_COMPLETION_CONCURRENT_UPDATE,
            validate_calendar_document,
        )

        validation_errors = validate_calendar_document(calendar)
        if validation_errors:
            return validation_errors

        payload = deepcopy(calendar)
        payload["updated_at_utc"] = utc_now_iso()
        new_digest = canonical_calendar_digest(payload)

        with self._lock:
            current = self._state.content_sha256
            expected = expected_fingerprint if expected_fingerprint is not None else current
            if expected != current:
                return [CALENDAR_COMPLETION_CONCURRENT_UPDATE]
            self._state = _MemoryState(
                document=payload,
                row_version=self._state.row_version + 1,
                content_sha256=new_digest,
            )
        return []

    def item_count(self) -> int:
        with self._lock:
            items = self._state.document.get("items", [])
            return len(items) if isinstance(items, list) else 0

    def force_replace(self, calendar: dict[str, Any]) -> list[str]:
        """Test/import helper: replace contents ignoring concurrency."""
        from silverman_blog_linkedin.editorial_calendar_plan import validate_calendar_document

        validation_errors = validate_calendar_document(calendar)
        if validation_errors:
            return validation_errors
        payload = deepcopy(calendar)
        if "updated_at_utc" not in payload:
            payload["updated_at_utc"] = utc_now_iso()
        digest = canonical_calendar_digest(payload)
        with self._lock:
            self._state = _MemoryState(
                document=payload,
                row_version=self._state.row_version + 1,
                content_sha256=digest,
            )
        return []


class PostgresCalendarStore:
    """PostgreSQL store targeting database `silverman_linkedin_db`."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_url_targets_canonical_db(database_url)

    @staticmethod
    def _ensure_url_targets_canonical_db(database_url: str) -> None:
        # Accept postgresql://.../silverman_linkedin_db optionally with query params.
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
                cur.execute(
                    """
                    INSERT INTO editorial_calendar (
                        calendar_id, schema_version, updated_at_utc, row_version, content_sha256
                    )
                    VALUES (%s, %s, %s, 0, %s)
                    ON CONFLICT (calendar_id) DO NOTHING
                    """,
                    (
                        MASTER_CALENDAR_ID,
                        "1",
                        utc_now_iso(),
                        canonical_calendar_digest(empty_calendar_document()),
                    ),
                )
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
                        SELECT schema_version, updated_at_utc, content_sha256
                        FROM editorial_calendar
                        WHERE calendar_id = %s
                        """,
                        (MASTER_CALENDAR_ID,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        empty = empty_calendar_document()
                        return empty, []
                    schema_version, updated_at_utc, _digest = row
                    cur.execute(
                        """
                        SELECT payload
                        FROM editorial_calendar_items
                        WHERE calendar_id = %s
                        ORDER BY item_id
                        """,
                        (MASTER_CALENDAR_ID,),
                    )
                    items = [dict(r[0]) for r in cur.fetchall()]
            return {
                "schema_version": schema_version,
                "updated_at_utc": updated_at_utc,
                "items": items,
            }, []
        except Exception:
            return None, [CALENDAR_STORE_UNAVAILABLE]

    def save(
        self,
        calendar: dict[str, Any],
        *,
        expected_fingerprint: str | None,
    ) -> list[str]:
        from silverman_blog_linkedin.editorial_calendar_plan import (
            CALENDAR_COMPLETION_CONCURRENT_UPDATE,
            CALENDAR_COMPLETION_WRITE_FAILED,
            validate_calendar_document,
        )

        validation_errors = validate_calendar_document(calendar)
        if validation_errors:
            return validation_errors

        payload = deepcopy(calendar)
        payload["updated_at_utc"] = utc_now_iso()
        new_digest = canonical_calendar_digest(payload)
        items = payload.get("items", [])
        if not isinstance(items, list):
            return ["calendar_schema_invalid"]

        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT content_sha256, row_version
                        FROM editorial_calendar
                        WHERE calendar_id = %s
                        FOR UPDATE
                        """,
                        (MASTER_CALENDAR_ID,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        current_digest = canonical_calendar_digest(empty_calendar_document())
                        row_version = 0
                    else:
                        current_digest, row_version = row
                    expected = (
                        expected_fingerprint
                        if expected_fingerprint is not None
                        else current_digest
                    )
                    if expected != current_digest:
                        conn.rollback()
                        return [CALENDAR_COMPLETION_CONCURRENT_UPDATE]

                    cur.execute(
                        """
                        INSERT INTO editorial_calendar (
                            calendar_id, schema_version, updated_at_utc, row_version, content_sha256
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (calendar_id) DO UPDATE SET
                            schema_version = EXCLUDED.schema_version,
                            updated_at_utc = EXCLUDED.updated_at_utc,
                            row_version = editorial_calendar.row_version + 1,
                            content_sha256 = EXCLUDED.content_sha256
                        """,
                        (
                            MASTER_CALENDAR_ID,
                            str(payload.get("schema_version", "1")),
                            str(payload["updated_at_utc"]),
                            row_version + 1,
                            new_digest,
                        ),
                    )
                    cur.execute(
                        "DELETE FROM editorial_calendar_items WHERE calendar_id = %s",
                        (MASTER_CALENDAR_ID,),
                    )
                    for item in items:
                        if not isinstance(item, dict):
                            conn.rollback()
                            return ["calendar_schema_invalid"]
                        item_id = str(item.get("item_id", ""))
                        cur.execute(
                            """
                            INSERT INTO editorial_calendar_items (calendar_id, item_id, payload)
                            VALUES (%s, %s, %s::jsonb)
                            """,
                            (MASTER_CALENDAR_ID, item_id, json.dumps(item)),
                        )
                conn.commit()
            return []
        except Exception:
            return [CALENDAR_COMPLETION_WRITE_FAILED]

    def item_count(self) -> int:
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM editorial_calendar_items
                        WHERE calendar_id = %s
                        """,
                        (MASTER_CALENDAR_ID,),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        except Exception as exc:
            raise RuntimeError(CALENDAR_STORE_UNAVAILABLE) from exc

    def force_replace(self, calendar: dict[str, Any]) -> list[str]:
        loaded, errors = self.load()
        if errors and loaded is None:
            return errors
        current_fp = None
        if loaded is not None:
            current_fp = canonical_calendar_digest(loaded)
        return self.save(calendar, expected_fingerprint=current_fp)


_store_lock = threading.RLock()
_store: CalendarStore | None = None


def reset_calendar_store_for_tests(store: CalendarStore | None = None) -> None:
    """Replace the process calendar store (tests only)."""
    global _store
    with _store_lock:
        _store = store


def create_calendar_store_from_url(database_url: str) -> CalendarStore:
    stripped = database_url.strip()
    if not stripped:
        raise ValueError(CALENDAR_STORE_NOT_CONFIGURED)
    if stripped.startswith(MEMORY_URL_PREFIX):
        return MemoryCalendarStore()
    return PostgresCalendarStore(stripped)


def get_calendar_store() -> CalendarStore:
    """Return the configured calendar store (lazy singleton)."""
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        raw = os.environ.get(ENV_CALENDAR_DATABASE_URL, "").strip()
        if not raw:
            raise RuntimeError(CALENDAR_STORE_NOT_CONFIGURED)
        _store = create_calendar_store_from_url(raw)
        return _store


def calendar_store_ready() -> dict[str, Any]:
    """Secret-safe readiness snapshot for health/status."""
    raw = os.environ.get(ENV_CALENDAR_DATABASE_URL, "").strip()
    if not raw:
        return {
            "calendar_store": "unconfigured",
            "calendar_store_ready": False,
            "calendar_database": CANONICAL_DATABASE_NAME,
        }
    try:
        store = get_calendar_store()
        ready = store.ping()
        return {
            "calendar_store": store.store_label(),
            "calendar_store_ready": ready,
            "calendar_database": CANONICAL_DATABASE_NAME,
        }
    except Exception:
        return {
            "calendar_store": "error",
            "calendar_store_ready": False,
            "calendar_database": CANONICAL_DATABASE_NAME,
        }
