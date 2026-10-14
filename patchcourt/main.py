"""Canonical application entrypoint.

The FastAPI application is defined in :mod:`patchcourt.api.app`; this module
re-exports it so ``uvicorn patchcourt.main:app`` works as well. The GitHub
webhook router is registered on the app in ``patchcourt/api/app.py``.
"""
from patchcourt.api.app import app

__all__ = ["app"]

if __name__ == "__main__":  # pragma: no cover - manual convenience
    import uvicorn

    uvicorn.run("patchcourt.main:app", host="0.0.0.0", port=8000)
