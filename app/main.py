# Canonical entry point is the root main.py — run with: uvicorn main:app --reload
# This shim ensures `uvicorn app.main:app` (e.g. old IDE run configs) also works.
from main import app  # noqa: F401
