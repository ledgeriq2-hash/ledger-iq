from __future__ import annotations

from typing import Iterable, Mapping, Sequence


def export_pdf(rows: Iterable[Mapping[str, object]], title: str | None = None) -> dict:
    """
    Placeholder PDF exporter.

    Returns a JSON-friendly representation describing the PDF document.
    """
    return {
        "title": title or "Report",
        "rows": list(rows),
    }


__all__ = ["export_pdf"]
