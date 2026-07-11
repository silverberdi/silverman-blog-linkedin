"""File-based LinkedIn OAuth token store with atomic writes and redaction."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REDACTED = "***"


@dataclass
class LinkedInTokenRecord:
    access_token: str
    refresh_token: str | None
    scope: str
    token_type: str
    created_at: str
    expires_at: str
    refresh_expires_at: str | None
    member_urn: str

    def __repr__(self) -> str:
        return (
            "LinkedInTokenRecord("
            f"access_token={REDACTED!r}, "
            f"refresh_token={REDACTED!r}, "
            f"scope={self.scope!r}, "
            f"token_type={self.token_type!r}, "
            f"created_at={self.created_at!r}, "
            f"expires_at={self.expires_at!r}, "
            f"refresh_expires_at={self.refresh_expires_at!r}, "
            f"member_urn={self.member_urn!r})"
        )

    def to_safe_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["access_token"] = REDACTED
        if payload.get("refresh_token"):
            payload["refresh_token"] = REDACTED
        return payload


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(data, indent=2) + "\n"
    tmp_path.write_text(payload, encoding="utf-8")
    for target in (tmp_path,):
        try:
            target.chmod(0o600)
        except OSError:
            pass
    try:
        tmp_path.replace(path)
    except OSError as exc:
        # Docker file bind-mounts reject rename into the mounted target (EBUSY).
        if exc.errno != 16:
            raise
        path.write_text(payload, encoding="utf-8")
        try:
            tmp_path.unlink()
        except OSError:
            pass
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_token_record(store_path: Path) -> LinkedInTokenRecord | None:
    """Load token record from store path when present and valid."""
    if not store_path.is_file():
        return None
    try:
        raw = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    access_token = raw.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        return None
    member_urn = raw.get("member_urn")
    if not isinstance(member_urn, str) or not member_urn.strip():
        return None
    return LinkedInTokenRecord(
        access_token=access_token.strip(),
        refresh_token=_optional_str(raw.get("refresh_token")),
        scope=str(raw.get("scope") or ""),
        token_type=str(raw.get("token_type") or "Bearer"),
        created_at=str(raw.get("created_at") or ""),
        expires_at=str(raw.get("expires_at") or ""),
        refresh_expires_at=_optional_str(raw.get("refresh_expires_at")),
        member_urn=member_urn.strip(),
    )


def save_token_record(store_path: Path, record: LinkedInTokenRecord) -> bool:
    """Persist token record atomically with restrictive permissions."""
    payload = asdict(record)
    try:
        _atomic_write_json(store_path, payload)
    except OSError:
        return False
    return True


def token_store_configured(store_path: Path) -> bool:
    """Return whether a token store path is configured (parent may be created on write)."""
    return bool(str(store_path).strip())


def token_present(store_path: Path) -> bool:
    """Return whether a non-empty token record exists."""
    return load_token_record(store_path) is not None


def parse_expires_at(expires_at: str) -> datetime | None:
    """Parse ISO-8601 expiry timestamp."""
    if not expires_at:
        return None
    normalized = expires_at.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def compute_expires_at(*, now: datetime, expires_in_seconds: int) -> str:
    """Compute ISO-8601 UTC expiry from now and lifetime seconds."""
    expires = now + timedelta(seconds=expires_in_seconds)
    return expires.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
