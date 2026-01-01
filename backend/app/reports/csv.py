from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence


def export_csv(rows: Iterable[Mapping[str, object]], fieldnames: Sequence[str] | None = None) -> str:
    """
    Export rows (list of dict-like objects) to CSV string.
    """
    rows = list(rows)
    if not rows:
        return ""

    if fieldnames is None:
        # Use keys from first row
        first_row = rows[0]
        fieldnames = list(first_row.keys())

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return buffer.getvalue()


__all__ = ["export_csv"]
