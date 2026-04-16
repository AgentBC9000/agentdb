import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings


def generate_api_key() -> tuple[str, str]:
    raw_key = f"adb_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(raw_key)
    return raw_key, hashed_key


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def get_trial_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=settings.TRIAL_DAYS)


def is_trial_expired(trial_expires_at: datetime) -> bool:
    return datetime.utcnow() > trial_expires_at
