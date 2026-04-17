import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.
    Returns (raw_key, hashed_key)
    raw_key is shown to the user ONCE — we store only the hash.
    """
    raw_key = f"adb_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(raw_key)
    return raw_key, hashed_key


def hash_api_key(raw_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def get_trial_expiry() -> datetime:
    """Return expiry datetime for a new trial key."""
    return datetime.now(timezone.utc) + timedelta(days=settings.TRIAL_DAYS)


def is_trial_expired(trial_expires_at: datetime) -> bool:
    """Check if a trial has expired."""
    now = datetime.now(timezone.utc)
    # Handle naive datetimes from DB by treating them as UTC
    if trial_expires_at.tzinfo is None:
        trial_expires_at = trial_expires_at.replace(tzinfo=timezone.utc)
    return now > trial_expires_at
