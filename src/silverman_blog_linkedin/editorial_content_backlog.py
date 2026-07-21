"""Editorial content backlog: validation and create/list/get/update helpers.

US-049 capture fields + US-050 dependencies (`depends_on_item_ids`) and
prioritization (`queue_rank`). Creating or updating items MUST NOT enable
LinkedIn API publish or write LinkedIn packages.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from silverman_blog_linkedin.editorial_content_backlog_store import (
    BACKLOG_CONCURRENT_UPDATE,
    BACKLOG_ITEM_NOT_FOUND,
    BACKLOG_STORE_NOT_CONFIGURED,
    BACKLOG_STORE_UNAVAILABLE,
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    EditorialContentBacklogStore,
    get_editorial_content_backlog_store,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

FORMAT_BLOG = "blog"
FORMAT_LINKEDIN = "linkedin"
FORMAT_BOTH = "both"
ALLOWED_FORMATS = frozenset({FORMAT_BLOG, FORMAT_LINKEDIN, FORMAT_BOTH})

PRIORITY_LOW = "low"
PRIORITY_MEDIUM = "medium"
PRIORITY_HIGH = "high"
ALLOWED_PRIORITIES = frozenset({PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH})

STATUS_IDEA = "idea"
STATUS_PLANNED = "planned"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"
STATUS_DROPPED = "dropped"
ALLOWED_STATUSES = frozenset(
    {
        STATUS_IDEA,
        STATUS_PLANNED,
        STATUS_IN_PROGRESS,
        STATUS_DONE,
        STATUS_DROPPED,
    }
)

MAX_TOPIC_LEN = 500
MAX_AUDIENCE_LEN = 500
MAX_OBJECTIVE_LEN = 2000
MAX_DERIVATIVE_HINT_LEN = 500
MAX_DERIVATIVE_NOTES_LEN = 2000
MAX_LINKEDIN_DERIVATIVES = 20
MAX_DEPENDS_ON_ITEM_IDS = 20

ERROR_TOPIC_REQUIRED = "topic_required"
ERROR_AUDIENCE_REQUIRED = "audience_required"
ERROR_OBJECTIVE_REQUIRED = "objective_required"
ERROR_FORMAT_INVALID = "format_invalid"
ERROR_PRIORITY_INVALID = "priority_invalid"
ERROR_STATUS_INVALID = "status_invalid"
ERROR_TARGET_DATE_INVALID = "target_date_invalid"
ERROR_LINKEDIN_DERIVATIVES_INVALID = "linkedin_derivatives_invalid"
ERROR_DEPENDENCY_INVALID = "depends_on_item_ids_invalid"
ERROR_DEPENDENCY_NOT_FOUND = "dependency_not_found"
ERROR_DEPENDENCY_SELF = "dependency_self"
ERROR_DEPENDENCY_CYCLE = "dependency_cycle"
ERROR_DEPENDENCY_DUPLICATE = "dependency_duplicate"
ERROR_QUEUE_RANK_INVALID = "queue_rank_invalid"
ERROR_REORDER_INVALID = "reorder_invalid"
ERROR_ITEM_NOT_FOUND = BACKLOG_ITEM_NOT_FOUND
ERROR_CONCURRENT_UPDATE = BACKLOG_CONCURRENT_UPDATE
ERROR_STORE_UNAVAILABLE = BACKLOG_STORE_UNAVAILABLE
ERROR_STORE_NOT_CONFIGURED = BACKLOG_STORE_NOT_CONFIGURED

_YYYY_MM_DD_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


@dataclass(frozen=True)
class BacklogItemSnapshot:
    """Secret-safe backlog item for HTTP responses."""

    item: dict[str, Any]

    def to_response_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item["item_id"],
            "topic": self.item["topic"],
            "audience": self.item["audience"],
            "objective": self.item["objective"],
            "format": self.item["format"],
            "priority": self.item["priority"],
            "status": self.item["status"],
            "target_date": self.item.get("target_date"),
            "linkedin_derivatives": list(self.item.get("linkedin_derivatives") or []),
            "depends_on_item_ids": list(self.item.get("depends_on_item_ids") or []),
            "queue_rank": int(self.item.get("queue_rank") or 0),
            "created_at_utc": self.item["created_at_utc"],
            "updated_at_utc": self.item["updated_at_utc"],
            "row_version": int(self.item["row_version"]),
        }


def _non_empty_string(value: Any, *, max_len: int) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > max_len:
        return None
    return stripped


def _optional_target_date(value: Any) -> tuple[str | None, bool]:
    """Return ``(normalized_or_none, ok)``. Empty string → null."""
    if value is None:
        return None, True
    if not isinstance(value, str):
        return None, False
    stripped = value.strip()
    if not stripped:
        return None, True
    match = _YYYY_MM_DD_RE.fullmatch(stripped)
    if not match:
        return None, False
    year, month, day = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    try:
        date(year, month, day)
    except ValueError:
        return None, False
    return f"{year:04d}-{month:02d}-{day:02d}", True


def _validate_linkedin_derivatives(value: Any) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return ``(normalized_list, errors)``."""
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], [
            {
                "field": "linkedin_derivatives",
                "code": ERROR_LINKEDIN_DERIVATIVES_INVALID,
                "message": "linkedin_derivatives must be a list of planning note objects",
            }
        ]
    if len(value) > MAX_LINKEDIN_DERIVATIVES:
        return [], [
            {
                "field": "linkedin_derivatives",
                "code": ERROR_LINKEDIN_DERIVATIVES_INVALID,
                "message": (
                    f"linkedin_derivatives must have at most {MAX_LINKEDIN_DERIVATIVES} items"
                ),
            }
        ]
    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            return [], [
                {
                    "field": f"linkedin_derivatives[{index}]",
                    "code": ERROR_LINKEDIN_DERIVATIVES_INVALID,
                    "message": "each LinkedIn derivative note must be an object",
                }
            ]
        extra = set(raw.keys()) - {"audience_hint", "format_hint", "notes"}
        if extra:
            return [], [
                {
                    "field": f"linkedin_derivatives[{index}]",
                    "code": ERROR_LINKEDIN_DERIVATIVES_INVALID,
                    "message": "LinkedIn derivative notes may only include audience_hint, format_hint, notes",
                }
            ]
        audience_hint = raw.get("audience_hint", "")
        format_hint = raw.get("format_hint", "")
        notes = raw.get("notes", "")
        for field_name, field_value, max_len in (
            ("audience_hint", audience_hint, MAX_DERIVATIVE_HINT_LEN),
            ("format_hint", format_hint, MAX_DERIVATIVE_HINT_LEN),
            ("notes", notes, MAX_DERIVATIVE_NOTES_LEN),
        ):
            if field_value is None:
                field_value = ""
            if not isinstance(field_value, str) or len(field_value) > max_len:
                return [], [
                    {
                        "field": f"linkedin_derivatives[{index}].{field_name}",
                        "code": ERROR_LINKEDIN_DERIVATIVES_INVALID,
                        "message": f"{field_name} must be a string of at most {max_len} characters",
                    }
                ]
        normalized.append(
            {
                "audience_hint": str(audience_hint).strip() if isinstance(audience_hint, str) else "",
                "format_hint": str(format_hint).strip() if isinstance(format_hint, str) else "",
                "notes": str(notes).strip() if isinstance(notes, str) else "",
            }
        )
    return normalized, []


def _validate_queue_rank_value(value: Any) -> tuple[int | None, list[dict[str, str]]]:
    """Return ``(rank_or_none, errors)``. ``None`` input means omitted (caller assigns)."""
    if value is None:
        return None, []
    if isinstance(value, bool) or not isinstance(value, int):
        return None, [
            {
                "field": "queue_rank",
                "code": ERROR_QUEUE_RANK_INVALID,
                "message": "queue_rank must be a non-negative integer",
            }
        ]
    if value < 0:
        return None, [
            {
                "field": "queue_rank",
                "code": ERROR_QUEUE_RANK_INVALID,
                "message": "queue_rank must be a non-negative integer",
            }
        ]
    return value, []


def _validate_depends_on_shape(
    value: Any,
) -> tuple[list[str] | None, list[dict[str, str]]]:
    """Shape-only validation: list of distinct non-empty strings, bounded length."""
    if value is None:
        return [], []
    if not isinstance(value, list):
        return None, [
            {
                "field": "depends_on_item_ids",
                "code": ERROR_DEPENDENCY_INVALID,
                "message": "depends_on_item_ids must be a list of backlog item ids",
            }
        ]
    if len(value) > MAX_DEPENDS_ON_ITEM_IDS:
        return None, [
            {
                "field": "depends_on_item_ids",
                "code": ERROR_DEPENDENCY_INVALID,
                "message": (
                    f"depends_on_item_ids must have at most "
                    f"{MAX_DEPENDS_ON_ITEM_IDS} items"
                ),
            }
        ]
    normalized: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, str) or not raw.strip():
            return None, [
                {
                    "field": f"depends_on_item_ids[{index}]",
                    "code": ERROR_DEPENDENCY_INVALID,
                    "message": "each dependency must be a non-empty item_id string",
                }
            ]
        dep_id = raw.strip()
        if dep_id in seen:
            return None, [
                {
                    "field": "depends_on_item_ids",
                    "code": ERROR_DEPENDENCY_DUPLICATE,
                    "message": f"depends_on_item_ids contains duplicate id {dep_id}",
                }
            ]
        seen.add(dep_id)
        normalized.append(dep_id)
    return normalized, []


def _dependency_graph_has_cycle(edges: dict[str, list[str]]) -> bool:
    """DFS cycle detection on directed graph item → depends_on."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in edges}

    def visit(node: str) -> bool:
        color[node] = GRAY
        for neighbor in edges.get(node, []):
            if neighbor not in color:
                color[neighbor] = WHITE
            if color[neighbor] == GRAY:
                return True
            if color[neighbor] == WHITE and visit(neighbor):
                return True
        color[node] = BLACK
        return False

    for node in list(edges):
        if color.get(node, WHITE) == WHITE and visit(node):
            return True
    return False


def _validate_depends_on_against_store(
    depends_on: list[str],
    *,
    self_item_id: str,
    store: EditorialContentBacklogStore,
) -> list[dict[str, str]]:
    """Existence, self-ref, and cycle checks. No partial persist."""
    errors: list[dict[str, str]] = []
    for dep_id in depends_on:
        if dep_id == self_item_id:
            errors.append(
                {
                    "field": "depends_on_item_ids",
                    "code": ERROR_DEPENDENCY_SELF,
                    "message": "an item cannot depend on itself",
                }
            )
            return errors

    for dep_id in depends_on:
        try:
            row, store_errors = store.get(dep_id)
        except RuntimeError as exc:
            code = str(exc)
            return [
                {
                    "field": "_store",
                    "code": code if code else ERROR_STORE_UNAVAILABLE,
                    "message": "backlog store read failed",
                }
            ]
        if store_errors:
            return _store_errors_to_structured(store_errors)
        if row is None:
            errors.append(
                {
                    "field": "depends_on_item_ids",
                    "code": ERROR_DEPENDENCY_NOT_FOUND,
                    "message": f"dependency item_id not found: {dep_id}",
                }
            )
            return errors

    try:
        existing_rows, store_errors = store.list_items(limit=MAX_LIST_LIMIT)
    except RuntimeError as exc:
        code = str(exc)
        return [
            {
                "field": "_store",
                "code": code if code else ERROR_STORE_UNAVAILABLE,
                "message": "backlog store read failed",
            }
        ]
    if store_errors:
        return _store_errors_to_structured(store_errors)

    edges: dict[str, list[str]] = {}
    for row in existing_rows:
        item_id = str(row["item_id"])
        if item_id == self_item_id:
            continue
        edges[item_id] = list(row.get("depends_on_item_ids") or [])
    edges[self_item_id] = list(depends_on)

    if _dependency_graph_has_cycle(edges):
        return [
            {
                "field": "depends_on_item_ids",
                "code": ERROR_DEPENDENCY_CYCLE,
                "message": (
                    "dependencies would create a cycle among backlog items; "
                    "remove the cycle and retry"
                ),
            }
        ]
    return []


def validate_backlog_write_document(
    document: dict[str, Any],
    *,
    require_queue_rank: bool = False,
) -> list[dict[str, str]]:
    """Validate capture fields, derivatives, deps shape, and queue_rank shape."""
    errors: list[dict[str, str]] = []

    topic = _non_empty_string(document.get("topic"), max_len=MAX_TOPIC_LEN)
    if topic is None:
        errors.append(
            {
                "field": "topic",
                "code": ERROR_TOPIC_REQUIRED,
                "message": "topic must be a non-empty string",
            }
        )

    audience = _non_empty_string(document.get("audience"), max_len=MAX_AUDIENCE_LEN)
    if audience is None:
        errors.append(
            {
                "field": "audience",
                "code": ERROR_AUDIENCE_REQUIRED,
                "message": "audience must be a non-empty string",
            }
        )

    objective = _non_empty_string(document.get("objective"), max_len=MAX_OBJECTIVE_LEN)
    if objective is None:
        errors.append(
            {
                "field": "objective",
                "code": ERROR_OBJECTIVE_REQUIRED,
                "message": "objective must be a non-empty string",
            }
        )

    fmt = document.get("format")
    if not isinstance(fmt, str) or fmt.strip() not in ALLOWED_FORMATS:
        errors.append(
            {
                "field": "format",
                "code": ERROR_FORMAT_INVALID,
                "message": "format must be one of: blog, linkedin, both",
            }
        )

    priority = document.get("priority")
    if not isinstance(priority, str) or priority.strip() not in ALLOWED_PRIORITIES:
        errors.append(
            {
                "field": "priority",
                "code": ERROR_PRIORITY_INVALID,
                "message": "priority must be one of: low, medium, high",
            }
        )

    status = document.get("status")
    if not isinstance(status, str) or status.strip() not in ALLOWED_STATUSES:
        errors.append(
            {
                "field": "status",
                "code": ERROR_STATUS_INVALID,
                "message": "status must be one of: idea, planned, in_progress, done, dropped",
            }
        )

    _, date_ok = _optional_target_date(document.get("target_date"))
    if not date_ok:
        errors.append(
            {
                "field": "target_date",
                "code": ERROR_TARGET_DATE_INVALID,
                "message": "target_date must be null or a valid YYYY-MM-DD calendar date",
            }
        )

    _, derivative_errors = _validate_linkedin_derivatives(
        document.get("linkedin_derivatives")
    )
    errors.extend(derivative_errors)

    _, dep_errors = _validate_depends_on_shape(document.get("depends_on_item_ids"))
    errors.extend(dep_errors)

    if "queue_rank" in document or require_queue_rank:
        rank_value = document.get("queue_rank")
        if require_queue_rank and rank_value is None and "queue_rank" not in document:
            errors.append(
                {
                    "field": "queue_rank",
                    "code": ERROR_QUEUE_RANK_INVALID,
                    "message": "queue_rank must be a non-negative integer",
                }
            )
        else:
            _, rank_errors = _validate_queue_rank_value(rank_value)
            errors.extend(rank_errors)
    elif document.get("queue_rank") is not None:
        _, rank_errors = _validate_queue_rank_value(document.get("queue_rank"))
        errors.extend(rank_errors)

    return errors


def normalize_backlog_write_document(document: dict[str, Any]) -> dict[str, Any]:
    """Return normalized mutable fields (caller must validate first)."""
    topic = _non_empty_string(document["topic"], max_len=MAX_TOPIC_LEN)
    audience = _non_empty_string(document["audience"], max_len=MAX_AUDIENCE_LEN)
    objective = _non_empty_string(document["objective"], max_len=MAX_OBJECTIVE_LEN)
    assert topic is not None and audience is not None and objective is not None
    target_date, date_ok = _optional_target_date(document.get("target_date"))
    assert date_ok
    derivatives, derivative_errors = _validate_linkedin_derivatives(
        document.get("linkedin_derivatives")
    )
    assert not derivative_errors
    depends_on, dep_errors = _validate_depends_on_shape(
        document.get("depends_on_item_ids")
    )
    assert not dep_errors and depends_on is not None
    fmt = document["format"]
    priority = document["priority"]
    status = document["status"]
    assert isinstance(fmt, str) and isinstance(priority, str) and isinstance(status, str)
    result: dict[str, Any] = {
        "topic": topic,
        "audience": audience,
        "objective": objective,
        "format": fmt.strip(),
        "priority": priority.strip(),
        "status": status.strip(),
        "target_date": target_date,
        "linkedin_derivatives": derivatives,
        "depends_on_item_ids": depends_on,
    }
    if "queue_rank" in document and document["queue_rank"] is not None:
        rank, rank_errors = _validate_queue_rank_value(document["queue_rank"])
        assert not rank_errors and rank is not None
        result["queue_rank"] = rank
    return result


def create_backlog_item(
    document: dict[str, Any],
    *,
    store: EditorialContentBacklogStore | None = None,
) -> tuple[BacklogItemSnapshot | None, list[dict[str, str]]]:
    """Validate and persist a new backlog item with server-assigned ``item_id``."""
    validation_errors = validate_backlog_write_document(document)
    if validation_errors:
        return None, validation_errors

    normalized = normalize_backlog_write_document(document)
    now = utc_now_iso()
    item_id = str(uuid.uuid4())
    active = store if store is not None else get_editorial_content_backlog_store()

    dep_errors = _validate_depends_on_against_store(
        list(normalized["depends_on_item_ids"]),
        self_item_id=item_id,
        store=active,
    )
    if dep_errors:
        return None, dep_errors

    if "queue_rank" not in normalized:
        try:
            next_rank, rank_store_errors = active.next_queue_rank()
        except RuntimeError as exc:
            code = str(exc)
            return None, [
                {
                    "field": "_store",
                    "code": code if code else ERROR_STORE_UNAVAILABLE,
                    "message": "backlog store write failed",
                }
            ]
        if rank_store_errors:
            return None, _store_errors_to_structured(rank_store_errors)
        normalized["queue_rank"] = next_rank

    payload = {
        **normalized,
        "item_id": item_id,
        "created_at_utc": now,
        "updated_at_utc": now,
    }
    try:
        row, store_errors = active.create(payload)
    except RuntimeError as exc:
        code = str(exc)
        return None, [
            {
                "field": "_store",
                "code": code if code else ERROR_STORE_UNAVAILABLE,
                "message": "backlog store write failed",
            }
        ]
    if store_errors or row is None:
        structured = _store_errors_to_structured(store_errors or [ERROR_STORE_UNAVAILABLE])
        return None, structured
    return BacklogItemSnapshot(item=row), []


def get_backlog_item(
    item_id: str,
    *,
    store: EditorialContentBacklogStore | None = None,
) -> tuple[BacklogItemSnapshot | None, list[dict[str, str]]]:
    """Load a single backlog item. Missing item → ``(None, [])`` (not a store failure)."""
    active = store if store is not None else get_editorial_content_backlog_store()
    try:
        row, store_errors = active.get(item_id)
    except RuntimeError as exc:
        code = str(exc)
        return None, [
            {
                "field": "_store",
                "code": code if code else ERROR_STORE_UNAVAILABLE,
                "message": "backlog store read failed",
            }
        ]
    if store_errors:
        return None, _store_errors_to_structured(store_errors)
    if row is None:
        return None, []
    return BacklogItemSnapshot(item=row), []


def list_backlog_items(
    *,
    status: str | None = None,
    priority: str | None = None,
    limit: int = DEFAULT_LIST_LIMIT,
    store: EditorialContentBacklogStore | None = None,
) -> tuple[list[BacklogItemSnapshot], list[dict[str, str]]]:
    """List backlog items under the prioritization sort contract."""
    filter_errors: list[dict[str, str]] = []
    if status is not None and status not in ALLOWED_STATUSES:
        filter_errors.append(
            {
                "field": "status",
                "code": ERROR_STATUS_INVALID,
                "message": "status filter must be one of: idea, planned, in_progress, done, dropped",
            }
        )
    if priority is not None and priority not in ALLOWED_PRIORITIES:
        filter_errors.append(
            {
                "field": "priority",
                "code": ERROR_PRIORITY_INVALID,
                "message": "priority filter must be one of: low, medium, high",
            }
        )
    if filter_errors:
        return [], filter_errors

    capped = max(1, min(int(limit), MAX_LIST_LIMIT))
    active = store if store is not None else get_editorial_content_backlog_store()
    try:
        rows, store_errors = active.list_items(
            status=status, priority=priority, limit=capped
        )
    except RuntimeError as exc:
        code = str(exc)
        return [], [
            {
                "field": "_store",
                "code": code if code else ERROR_STORE_UNAVAILABLE,
                "message": "backlog store read failed",
            }
        ]
    if store_errors:
        return [], _store_errors_to_structured(store_errors)
    return [BacklogItemSnapshot(item=row) for row in rows], []


def update_backlog_item(
    item_id: str,
    document: dict[str, Any],
    *,
    expected_row_version: int | None = None,
    store: EditorialContentBacklogStore | None = None,
) -> tuple[BacklogItemSnapshot | None, list[dict[str, str]]]:
    """Validate and update an existing backlog item (full mutable document)."""
    # Updates must include queue_rank (or retain via document); if omitted, keep
    # current rank after load — validate shape when present.
    validation_errors = validate_backlog_write_document(document)
    if validation_errors:
        return None, validation_errors

    active = store if store is not None else get_editorial_content_backlog_store()
    existing, get_errors = get_backlog_item(item_id, store=active)
    if get_errors:
        return None, get_errors
    if existing is None:
        return None, [
            {
                "field": "item_id",
                "code": ERROR_ITEM_NOT_FOUND,
                "message": "backlog item not found",
            }
        ]

    normalized = normalize_backlog_write_document(document)
    if "queue_rank" not in normalized:
        normalized["queue_rank"] = int(existing.item.get("queue_rank") or 0)

    dep_errors = _validate_depends_on_against_store(
        list(normalized["depends_on_item_ids"]),
        self_item_id=item_id,
        store=active,
    )
    if dep_errors:
        return None, dep_errors

    payload = {
        **normalized,
        "updated_at_utc": utc_now_iso(),
    }
    try:
        row, store_errors = active.update(
            item_id,
            payload,
            expected_row_version=expected_row_version,
        )
    except RuntimeError as exc:
        code = str(exc)
        return None, [
            {
                "field": "_store",
                "code": code if code else ERROR_STORE_UNAVAILABLE,
                "message": "backlog store write failed",
            }
        ]
    if store_errors or row is None:
        return None, _store_errors_to_structured(store_errors or [ERROR_STORE_UNAVAILABLE])
    return BacklogItemSnapshot(item=row), []


def reorder_backlog_items(
    ordered_item_ids: list[str],
    *,
    store: EditorialContentBacklogStore | None = None,
) -> tuple[list[BacklogItemSnapshot] | None, list[dict[str, str]]]:
    """Reassign contiguous ``queue_rank`` values ``0..n-1`` from ordered ids."""
    if not isinstance(ordered_item_ids, list):
        return None, [
            {
                "field": "ordered_item_ids",
                "code": ERROR_REORDER_INVALID,
                "message": "ordered_item_ids must be a list of backlog item ids",
            }
        ]
    if not ordered_item_ids:
        return None, [
            {
                "field": "ordered_item_ids",
                "code": ERROR_REORDER_INVALID,
                "message": "ordered_item_ids must not be empty",
            }
        ]
    normalized: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(ordered_item_ids):
        if not isinstance(raw, str) or not raw.strip():
            return None, [
                {
                    "field": f"ordered_item_ids[{index}]",
                    "code": ERROR_REORDER_INVALID,
                    "message": "each ordered id must be a non-empty item_id string",
                }
            ]
        item_id = raw.strip()
        if item_id in seen:
            return None, [
                {
                    "field": "ordered_item_ids",
                    "code": ERROR_REORDER_INVALID,
                    "message": f"ordered_item_ids contains duplicate id {item_id}",
                }
            ]
        seen.add(item_id)
        normalized.append(item_id)

    active = store if store is not None else get_editorial_content_backlog_store()
    try:
        rows, store_errors = active.reorder(normalized)
    except RuntimeError as exc:
        code = str(exc)
        return None, [
            {
                "field": "_store",
                "code": code if code else ERROR_STORE_UNAVAILABLE,
                "message": "backlog store write failed",
            }
        ]
    if store_errors or rows is None:
        return None, _store_errors_to_structured(store_errors or [ERROR_STORE_UNAVAILABLE])
    return [BacklogItemSnapshot(item=row) for row in rows], []


def _store_errors_to_structured(codes: list[str]) -> list[dict[str, str]]:
    structured: list[dict[str, str]] = []
    for code in codes:
        if code == ERROR_ITEM_NOT_FOUND:
            structured.append(
                {
                    "field": "item_id",
                    "code": code,
                    "message": "backlog item not found",
                }
            )
        elif code == ERROR_CONCURRENT_UPDATE:
            structured.append(
                {
                    "field": "row_version",
                    "code": code,
                    "message": "backlog item was updated concurrently; reload and retry",
                }
            )
        elif code == ERROR_STORE_NOT_CONFIGURED:
            structured.append(
                {
                    "field": "_store",
                    "code": code,
                    "message": "backlog store is not configured",
                }
            )
        else:
            structured.append(
                {
                    "field": "_store",
                    "code": code,
                    "message": "backlog store is unavailable",
                }
            )
    return structured
