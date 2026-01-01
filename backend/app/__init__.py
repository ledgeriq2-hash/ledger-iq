from __future__ import annotations

"""
Ledger IQ backend package.

Do NOT import `settings` at import-time because it requires env vars and will
raise ValidationError if they aren't loaded yet (e.g. when running scripts).
Import settings lazily from `app.config` where needed.
"""

from .config import get_settings

__all__ = ["get_settings"]
