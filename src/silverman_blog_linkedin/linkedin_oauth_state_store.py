"""Server-side OAuth state store with TTL and single-use validation."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from silverman_blog_linkedin.linkedin_token_store import _atomic_write_json


@dataclass(frozen=True)
class OAuthStateEntry:
    created_at: str
    expires_at: str


def state_store_path_for_token_store(token_store_path: Path) -> Path:
    """Resolve OAuth state file path alongside token store parent directory."""
    return token_store_path.parent / "linkedin-oauth-state.json"


def generate_oauth_state() -> str:
    """Generate a cryptographically secure OAuth state value."""
    return secrets.token_urlsafe(32)


def _load_state_map(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: value
        for key, value in raw.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _save_state_map(path: Path, state_map: dict[str, dict[str, str]]) -> bool:
    try:
        _atomic_write_json(path, state_map)
    except OSError:
        return False
    return True


def _parse_utc(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _prune_expired(
    state_map: dict[str, dict[str, str]], *, now: datetime
) -> dict[str, dict[str, str]]:
    pruned: dict[str, dict[str, str]] = {}
    for state, entry in state_map.items():
        expires_at = _parse_utc(str(entry.get("expires_at", "")))
        if expires_at is None or expires_at <= now:
            continue
        pruned[state] = entry
    return pruned


def create_oauth_state(
    path: Path,
    *,
    ttl_seconds: int,
    now: datetime | None = None,
) -> str:
    """Create and persist a new OAuth state with TTL."""
    current = now or datetime.now(timezone.utc)
    state = generate_oauth_state()
    expires = current + timedelta(seconds=ttl_seconds)
    entry = {
        "created_at": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    state_map = _prune_expired(_load_state_map(path), now=current)
    state_map[state] = entry
    if not _save_state_map(path, state_map):
        raise OSError("oauth_state_write_failed")
    return state


def validate_and_consume_oauth_state(
    path: Path,
    state: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Validate state exists, is not expired, and delete it (single-use)."""
    if not state.strip():
        return False
    current = now or datetime.now(timezone.utc)
    state_map = _prune_expired(_load_state_map(path), now=current)
    entry = state_map.get(state)
    if entry is None:
        _save_state_map(path, state_map)
        return False
    expires_at = _parse_utc(str(entry.get("expires_at", "")))
    if expires_at is None or expires_at <= current:
        state_map.pop(state, None)
        _save_state_map(path, state_map)
        return False
    state_map.pop(state, None)
    if not _save_state_map(path, state_map):
        return False
    return True


def prune_expired_states(path: Path, *, now: datetime | None = None) -> None:
    """Remove expired OAuth state entries."""
    current = now or datetime.now(timezone.utc)
    state_map = _prune_expired(_load_state_map(path), now=current)
    _save_state_map(path, state_map)
