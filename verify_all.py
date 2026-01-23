from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _resolve_verifier_path(repo_root: Path, sprint: int) -> Path | None:
    root_candidate = repo_root / f"verify_sprint{sprint}.py"
    if root_candidate.exists():
        return root_candidate
    backend_candidate = repo_root / "backend" / "scripts" / f"verify_sprint{sprint}.py"
    if backend_candidate.exists():
        return backend_candidate
    return None


def _run_verifier(repo_root: Path, sprint: int, path: Path) -> None:
    env = os.environ.copy()
    env.setdefault("ENVIRONMENT", "development")
    env.setdefault("CSRF_ENABLED", "false")
    env.setdefault("BILLING_ENABLED", "false")
    env.setdefault("FEATURE_OPTIONAL_ROUTES", "true")

    print(f"verify_all: running sprint {sprint} -> {path.relative_to(repo_root)}")
    result = subprocess.run([sys.executable, str(path)], cwd=str(repo_root), env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    sprints: list[int] = []

    if _resolve_verifier_path(repo_root, 2):
        sprints.append(2)
    sprints.extend([3, 4, 5, 6, 7, 8, 9])

    for sprint in sprints:
        path = _resolve_verifier_path(repo_root, sprint)
        if not path:
            raise SystemExit(f"verify_all: verifier not found for sprint {sprint}")
        _run_verifier(repo_root, sprint, path)

    print("verify_all: all verifiers passed")


if __name__ == "__main__":
    main()
