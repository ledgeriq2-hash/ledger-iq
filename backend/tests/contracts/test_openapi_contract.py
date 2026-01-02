from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def test_openapi_contract_snapshot():
    snapshot_path = Path(__file__).with_name("openapi_snapshot.json")
    assert snapshot_path.exists(), "OpenAPI snapshot is missing"
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    app.openapi_schema = None
    actual = app.openapi()
    assert actual == expected
