from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from celery import shared_task

from app.reports.pdf import export_pdf


def _write_pdf(filename: str, rows: list[dict]) -> str:
    output_dir = Path("report_exports")
    output_dir.mkdir(exist_ok=True)
    pdf_bytes = export_pdf(rows, title="Scheduled Report")
    file_path = output_dir / filename
    file_path.write_bytes(pdf_bytes)
    return str(file_path)


@shared_task(name="app.tasks.report_tasks.generate_daily_reports")
def generate_daily_reports() -> dict:
    today = datetime.now(UTC).date()
    rows = [{"date": str(today), "type": "daily", "generated_at": datetime.now(UTC).isoformat()}]
    path = _write_pdf(f"daily_{today}.pdf", rows)
    return {"status": "ok", "type": "daily", "path": path}


@shared_task(name="app.tasks.report_tasks.generate_weekly_reports")
def generate_weekly_reports() -> dict:
    today = datetime.now(UTC).date()
    rows = [{"week_of": str(today), "type": "weekly", "generated_at": datetime.now(UTC).isoformat()}]
    path = _write_pdf(f"weekly_{today}.pdf", rows)
    return {"status": "ok", "type": "weekly", "path": path}


__all__ = ["generate_daily_reports", "generate_weekly_reports"]
