from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_sha256(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object (dict)")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["canonical_sha256"]
