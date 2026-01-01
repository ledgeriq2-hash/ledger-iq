from __future__ import annotations

import io
from collections.abc import Iterable, Mapping
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def export_pdf(rows: Iterable[Mapping[str, Any]], title: str | None = None) -> bytes:
    """
    Render a minimal PDF containing the given rows.

    Returns binary PDF bytes suitable for download/response bodies.
    """
    rows = list(rows)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(title or "Report")
    width, height = letter
    y = height - inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, y, title or "Report")
    y -= 0.4 * inch
    c.setFont("Helvetica", 10)
    for row in rows:
        line = ", ".join(f"{k}: {v}" for k, v in row.items())
        if y < inch:
            c.showPage()
            y = height - inch
            c.setFont("Helvetica", 10)
        c.drawString(inch, y, line)
        y -= 0.25 * inch
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


__all__ = ["export_pdf"]
