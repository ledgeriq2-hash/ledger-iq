from __future__ import annotations

from fastapi import Request


async def enforce_rate_limit(request: Request, scope: str, limit: int, window_seconds: int = 60) -> None:
    """
    Disabled for local/dev runtime.
    """
    return


__all__ = ["enforce_rate_limit"]
