from __future__ import annotations

from app.core.settings import Settings, get_settings as _get_settings

settings: Settings = _get_settings()


def get_settings() -> Settings:
    """Return application settings singleton."""
    return settings


__all__ = ["Settings", "get_settings", "settings"]
