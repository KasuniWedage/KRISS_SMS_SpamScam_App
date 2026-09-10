"""Expose the FastAPI application when Uvicorn is run from the repo root.

This keeps the short development command working from either location:
    uvicorn app.main:app --reload
"""

import os
import sys
from pathlib import Path


REPOSITORY_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPOSITORY_DIR / "backend"

# Backend configuration intentionally supports relative SQLite, model and
# credential paths. Resolve those paths from the backend directory just as the
# original backend-local launch command does.
repository_path = str(REPOSITORY_DIR)
if repository_path not in sys.path:
    sys.path.insert(0, repository_path)
os.chdir(BACKEND_DIR)

from backend.app.main import app  # noqa: E402


__all__ = ["app"]
