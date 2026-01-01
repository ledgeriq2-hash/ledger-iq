from __future__ import annotations

from functools import lru_cache

from app.core.settings import Settings
from app.core.settings import get_settings as _get_settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Lazy & cached settings loader.

    IMPORTANT:
    - Do NOT initialize settings at import time.
    - This avoids ValidationError when env vars are not loaded yet
      (e.g. when running scripts like bootstrap_demo).
    """
    return _get_settings()


__all__ = ["Settings", "get_settings"]
