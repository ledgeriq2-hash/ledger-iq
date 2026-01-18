from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    script = Path(__file__).resolve().parent / "backend" / "scripts" / "verify_sprint8.py"
    if not script.exists():
        raise SystemExit("verify_sprint8: backend/scripts/verify_sprint8.py not found")
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
