"""Editorial content backlog store (Postgres ``silverman_linkedin_db`` or memory).

Reuses ``SILVERMAN_CALENDAR_DATABASE_URL`` targeting the same database as the
editorial calendar (US-041 / ADR-0004). Tests use ``memory://``.
"""

from __future__ import annotations

import json
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

BACKLOG_STORE_NOT_CONFIGURED = "editorial_content_backlog_store_not_configured"
BACKLOG_STORE_UNAVAILABLE = "editorial_content_backlog_store_unavailable"
BACKLOG_CONCURRENT_UPDATE = "editorial_content_backlog_concurrent_update"
BACKLOG_ITEM_NOT_FOUND = "editorial_content_backlog_item_not_found"

DEFAULT_LIST_LIMIT = 100
MAX_LIST_LIMIT = 200

# Priority band for list sort: high before medium before low.
PRIORITY_BAND_ORDER = {"high": 0, "medium": 1, "low": 2}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS editorial_content_backlog_items (
    item_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    audience TEXT NOT NULL,
    objective TEXT NOT NULL,
    format TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    target_date TEXT,
    linkedin_derivatives JSONB NOT NULL DEFAULT '[]'::jsonb,
    depends_on_item_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    queue_rank INTEGER NOT NULL DEFAULT 0,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    row_version BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS editorial_content_backlog_items_updated_idx
    ON editorial_content_backlog_items (updated_at_utc DESC);
CREATE INDEX IF NOT EXISTS editorial_content_backlog_items_queue_rank_idx
    ON editorial_content_backlog_items (queue_rank ASC);
"""

SCHEMA_MIGRATE_SQL = """
ALTER TABLE editorial_content_backlog_items
    ADD COLUMN IF NOT EXISTS depends_on_item_ids JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE editorial_content_backlog_items
    ADD COLUMN IF NOT EXISTS queue_rank INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS editorial_content_backlog_items_queue_rank_idx
    ON editorial_content_backlog_items (queue_rank ASC);
"""

_ITEM_COLUMNS = (
    "item_id",
    "topic",
    "audience",
    "objective",
    "format",
    "priority",
    "status",
    "target_date",
    "linkedin_derivatives",
    "depends_on_item_ids",
    "queue_rank",
    "created_at_utc",
    "updated_at_utc",
    "row_version",
)


def _priority_band(priority: Any) -> int:
    if isinstance(priority, str):
        return PRIORITY_BAND_ORDER.get(priority, 99)
    return 99


def _sort_items_prioritized(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """queue_rank ASC, priority band (high < medium < low), updated_at DESC."""
    return sorted(
        rows,
        key=lambda r: (
            int(r.get("queue_rank") or 0),
            _priority_band(r.get("priority")),
            "".join(chr(255 - ord(c)) for c in str(r.get("updated_at_utc") or "")),
            "".join(chr(255 - ord(c)) for c in str(r.get("item_id") or "")),
        ),
    )


def _parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    return value


def _row_to_item(row: tuple[Any, ...]) -> dict[str, Any]:
    derivatives = _parse_json_list(row[8])
    depends_on_ids = [str(x) for x in _parse_json_list(row[9])]
    return {
        "item_id": row[0],
        "topic": row[1],
        "audience": row[2],
        "objective": row[3],
        "format": row[4],
        "priority": row[5],
        "status": row[6],
        "target_date": row[7],
        "linkedin_derivatives": deepcopy(derivatives),
        "depends_on_item_ids": list(depends_on_ids),
        "queue_rank": int(row[10]),
        "created_at_utc": row[11],
        "updated_at_utc": row[12],
        "row_version": int(row[13]),
    }


class EditorialContentBacklogStore(Protocol):
    def store_label(self) -> str: ...

    def ensure_schema(self) -> None: ...

    def ping(self) -> bool: ...

    def create(self, document: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]: ...

    def get(self, item_id: str) -> tuple[dict[str, Any] | None, list[str]]: ...

    def list_items(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> tuple[list[dict[str, Any]], list[str]]: ...

    def update(
        self,
        item_id: str,
        document: dict[str, Any],
        *,
        expected_row_version: int | None,
    ) -> tuple[dict[str, Any] | None, list[str]]: ...

    def next_queue_rank(self) -> tuple[int, list[str]]: ...

    def reorder(
        self, ordered_item_ids: list[str]
    ) -> tuple[list[dict[str, Any]] | None, list[str]]: ...


class MemoryEditorialContentBacklogStore:
    """Process-local store for unit tests (``SILVERMAN_CALENDAR_DATABASE_URL=memory://``)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, dict[str, Any]] = {}

    def store_label(self) -> str:
        return "memory:test"

    def ensure_schema(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def next_queue_rank(self) -> tuple[int, list[str]]:
        with self._lock:
            if not self._items:
                return 0, []
            return max(int(r.get("queue_rank") or 0) for r in self._items.values()) + 1, []

    def create(self, document: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        payload = deepcopy(document)
        now = utc_now_iso()
        payload.setdefault("created_at_utc", now)
        payload.setdefault("updated_at_utc", now)
        payload.setdefault("depends_on_item_ids", [])
        if "queue_rank" not in payload:
            next_rank, _ = self.next_queue_rank()
            payload["queue_rank"] = next_rank
        item_id = str(payload["item_id"])
        with self._lock:
            if item_id in self._items:
                return None, [BACKLOG_CONCURRENT_UPDATE]
            row = {
                **{k: payload[k] for k in _ITEM_COLUMNS if k != "row_version"},
                "depends_on_item_ids": list(payload.get("depends_on_item_ids") or []),
                "queue_rank": int(payload["queue_rank"]),
                "row_version": 1,
            }
            self._items[item_id] = row
            return deepcopy(row), []

    def get(self, item_id: str) -> tuple[dict[str, Any] | None, list[str]]:
        with self._lock:
            row = self._items.get(item_id)
            if row is None:
                return None, []
            return deepcopy(row), []

    def list_items(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        capped = max(1, min(int(limit), MAX_LIST_LIMIT))
        with self._lock:
            rows = list(self._items.values())
        if status is not None:
            rows = [r for r in rows if r.get("status") == status]
        if priority is not None:
            rows = [r for r in rows if r.get("priority") == priority]
        rows = _sort_items_prioritized(rows)
        return [deepcopy(r) for r in rows[:capped]], []

    def update(
        self,
        item_id: str,
        document: dict[str, Any],
        *,
        expected_row_version: int | None,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        payload = deepcopy(document)
        payload.setdefault("updated_at_utc", utc_now_iso())
        with self._lock:
            current = self._items.get(item_id)
            if current is None:
                return None, [BACKLOG_ITEM_NOT_FOUND]
            current_version = int(current["row_version"])
            if (
                expected_row_version is not None
                and expected_row_version != current_version
            ):
                return None, [BACKLOG_CONCURRENT_UPDATE]
            next_version = current_version + 1
            row = {
                "item_id": item_id,
                "topic": payload["topic"],
                "audience": payload["audience"],
                "objective": payload["objective"],
                "format": payload["format"],
                "priority": payload["priority"],
                "status": payload["status"],
                "target_date": payload.get("target_date"),
                "linkedin_derivatives": deepcopy(payload.get("linkedin_derivatives") or []),
                "depends_on_item_ids": list(payload.get("depends_on_item_ids") or []),
                "queue_rank": int(payload["queue_rank"]),
                "created_at_utc": current["created_at_utc"],
                "updated_at_utc": payload["updated_at_utc"],
                "row_version": next_version,
            }
            self._items[item_id] = row
            return deepcopy(row), []

    def reorder(
        self, ordered_item_ids: list[str]
    ) -> tuple[list[dict[str, Any]] | None, list[str]]:
        now = utc_now_iso()
        with self._lock:
            for item_id in ordered_item_ids:
                if item_id not in self._items:
                    return None, [BACKLOG_ITEM_NOT_FOUND]
            for rank, item_id in enumerate(ordered_item_ids):
                current = self._items[item_id]
                self._items[item_id] = {
                    **current,
                    "queue_rank": rank,
                    "updated_at_utc": now,
                    "row_version": int(current["row_version"]) + 1,
                }
            rows = _sort_items_prioritized(list(self._items.values()))
            return [deepcopy(r) for r in rows], []

    def clear(self) -> None:
        """Test helper: remove all backlog items."""
        with self._lock:
            self._items.clear()


class PostgresEditorialContentBacklogStore:
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
                cur.execute(SCHEMA_MIGRATE_SQL)
                self._backfill_queue_ranks(cur)
            conn.commit()

    def _backfill_queue_ranks(self, cur: Any) -> None:
        """Assign contiguous ranks when all existing rows still share default 0."""
        cur.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT queue_rank), COALESCE(MIN(queue_rank), 0)
            FROM editorial_content_backlog_items
            """
        )
        total, distinct_ranks, min_rank = cur.fetchone()
        if total is None or int(total) <= 1:
            return
        if int(distinct_ranks) != 1 or int(min_rank) != 0:
            return
        cur.execute(
            """
            WITH ordered AS (
                SELECT item_id,
                       (ROW_NUMBER() OVER (
                           ORDER BY updated_at_utc DESC, item_id DESC
                       ) - 1)::integer AS rn
                FROM editorial_content_backlog_items
            )
            UPDATE editorial_content_backlog_items AS e
            SET queue_rank = ordered.rn
            FROM ordered
            WHERE e.item_id = ordered.item_id
            """
        )

    def ping(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception:
            return False

    def next_queue_rank(self) -> tuple[int, list[str]]:
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COALESCE(MAX(queue_rank), -1) + 1
                        FROM editorial_content_backlog_items
                        """
                    )
                    row = cur.fetchone()
            return int(row[0]) if row else 0, []
        except Exception:
            return 0, [BACKLOG_STORE_UNAVAILABLE]

    def create(self, document: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            self.ensure_schema()
            payload = deepcopy(document)
            now = utc_now_iso()
            payload.setdefault("created_at_utc", now)
            payload.setdefault("updated_at_utc", now)
            payload.setdefault("depends_on_item_ids", [])
            if "queue_rank" not in payload:
                next_rank, rank_errors = self.next_queue_rank()
                if rank_errors:
                    return None, rank_errors
                payload["queue_rank"] = next_rank
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO editorial_content_backlog_items (
                            item_id, topic, audience, objective, format, priority,
                            status, target_date, linkedin_derivatives,
                            depends_on_item_ids, queue_rank,
                            created_at_utc, updated_at_utc, row_version
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                            %s::jsonb, %s, %s, %s, %s
                        )
                        RETURNING
                            item_id, topic, audience, objective, format, priority,
                            status, target_date, linkedin_derivatives,
                            depends_on_item_ids, queue_rank,
                            created_at_utc, updated_at_utc, row_version
                        """,
                        (
                            payload["item_id"],
                            payload["topic"],
                            payload["audience"],
                            payload["objective"],
                            payload["format"],
                            payload["priority"],
                            payload["status"],
                            payload.get("target_date"),
                            json.dumps(payload.get("linkedin_derivatives") or []),
                            json.dumps(payload.get("depends_on_item_ids") or []),
                            int(payload["queue_rank"]),
                            payload["created_at_utc"],
                            payload["updated_at_utc"],
                            1,
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            assert row is not None
            return _row_to_item(row), []
        except Exception:
            return None, [BACKLOG_STORE_UNAVAILABLE]

    def get(self, item_id: str) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            self.ensure_schema()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            item_id, topic, audience, objective, format, priority,
                            status, target_date, linkedin_derivatives,
                            depends_on_item_ids, queue_rank,
                            created_at_utc, updated_at_utc, row_version
                        FROM editorial_content_backlog_items
                        WHERE item_id = %s
                        """,
                        (item_id,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return None, []
                    return _row_to_item(row), []
        except Exception:
            return None, [BACKLOG_STORE_UNAVAILABLE]

    def list_items(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        try:
            self.ensure_schema()
            capped = max(1, min(int(limit), MAX_LIST_LIMIT))
            clauses: list[str] = []
            params: list[Any] = []
            if status is not None:
                clauses.append("status = %s")
                params.append(status)
            if priority is not None:
                clauses.append("priority = %s")
                params.append(priority)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(capped)
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT
                            item_id, topic, audience, objective, format, priority,
                            status, target_date, linkedin_derivatives,
                            depends_on_item_ids, queue_rank,
                            created_at_utc, updated_at_utc, row_version
                        FROM editorial_content_backlog_items
                        {where}
                        ORDER BY
                            queue_rank ASC,
                            CASE priority
                                WHEN 'high' THEN 0
                                WHEN 'medium' THEN 1
                                WHEN 'low' THEN 2
                                ELSE 99
                            END ASC,
                            updated_at_utc DESC,
                            item_id DESC
                        LIMIT %s
                        """,
                        tuple(params),
                    )
                    rows = cur.fetchall()
            return [_row_to_item(row) for row in rows], []
        except Exception:
            return [], [BACKLOG_STORE_UNAVAILABLE]

    def update(
        self,
        item_id: str,
        document: dict[str, Any],
        *,
        expected_row_version: int | None,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            self.ensure_schema()
            payload = deepcopy(document)
            payload.setdefault("updated_at_utc", utc_now_iso())
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT row_version
                        FROM editorial_content_backlog_items
                        WHERE item_id = %s
                        FOR UPDATE
                        """,
                        (item_id,),
                    )
                    existing = cur.fetchone()
                    if existing is None:
                        return None, [BACKLOG_ITEM_NOT_FOUND]
                    current_version = int(existing[0])
                    if (
                        expected_row_version is not None
                        and expected_row_version != current_version
                    ):
                        return None, [BACKLOG_CONCURRENT_UPDATE]
                    next_version = current_version + 1
                    cur.execute(
                        """
                        UPDATE editorial_content_backlog_items SET
                            topic = %s,
                            audience = %s,
                            objective = %s,
                            format = %s,
                            priority = %s,
                            status = %s,
                            target_date = %s,
                            linkedin_derivatives = %s::jsonb,
                            depends_on_item_ids = %s::jsonb,
                            queue_rank = %s,
                            updated_at_utc = %s,
                            row_version = %s
                        WHERE item_id = %s
                        RETURNING
                            item_id, topic, audience, objective, format, priority,
                            status, target_date, linkedin_derivatives,
                            depends_on_item_ids, queue_rank,
                            created_at_utc, updated_at_utc, row_version
                        """,
                        (
                            payload["topic"],
                            payload["audience"],
                            payload["objective"],
                            payload["format"],
                            payload["priority"],
                            payload["status"],
                            payload.get("target_date"),
                            json.dumps(payload.get("linkedin_derivatives") or []),
                            json.dumps(payload.get("depends_on_item_ids") or []),
                            int(payload["queue_rank"]),
                            payload["updated_at_utc"],
                            next_version,
                            item_id,
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            assert row is not None
            return _row_to_item(row), []
        except Exception:
            return None, [BACKLOG_STORE_UNAVAILABLE]

    def reorder(
        self, ordered_item_ids: list[str]
    ) -> tuple[list[dict[str, Any]] | None, list[str]]:
        try:
            self.ensure_schema()
            now = utc_now_iso()
            with self._connect() as conn:
                with conn.cursor() as cur:
                    for item_id in ordered_item_ids:
                        cur.execute(
                            """
                            SELECT item_id FROM editorial_content_backlog_items
                            WHERE item_id = %s
                            FOR UPDATE
                            """,
                            (item_id,),
                        )
                        if cur.fetchone() is None:
                            return None, [BACKLOG_ITEM_NOT_FOUND]
                    for rank, item_id in enumerate(ordered_item_ids):
                        cur.execute(
                            """
                            UPDATE editorial_content_backlog_items SET
                                queue_rank = %s,
                                updated_at_utc = %s,
                                row_version = row_version + 1
                            WHERE item_id = %s
                            """,
                            (rank, now, item_id),
                        )
                conn.commit()
            return self.list_items(limit=MAX_LIST_LIMIT)
        except Exception:
            return None, [BACKLOG_STORE_UNAVAILABLE]


_store_lock = threading.RLock()
_store: EditorialContentBacklogStore | None = None


def reset_editorial_content_backlog_store_for_tests(
    store: EditorialContentBacklogStore | None = None,
) -> None:
    """Replace the process backlog store (tests only)."""
    global _store
    with _store_lock:
        _store = store


def create_editorial_content_backlog_store_from_url(
    database_url: str,
) -> EditorialContentBacklogStore:
    stripped = database_url.strip()
    if not stripped:
        raise ValueError(BACKLOG_STORE_NOT_CONFIGURED)
    if stripped.startswith(MEMORY_URL_PREFIX):
        return MemoryEditorialContentBacklogStore()
    return PostgresEditorialContentBacklogStore(stripped)


def get_editorial_content_backlog_store() -> EditorialContentBacklogStore:
    """Return the configured backlog store (lazy singleton; same URL as calendar)."""
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        raw = os.environ.get(ENV_CALENDAR_DATABASE_URL, "").strip()
        if not raw:
            raise RuntimeError(BACKLOG_STORE_NOT_CONFIGURED)
        _store = create_editorial_content_backlog_store_from_url(raw)
        return _store
