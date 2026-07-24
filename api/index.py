"""Vercel Python serverless entrypoint.

Vercel serves the ASGI `app` exposed here. `vercel.json` rewrites the API paths
(`/api/*`, `/health`, `/features`) to this function while the built React app is
served as static files from `frontend/dist`.

The FastAPI application lives in `backend/app`, so we put that directory on the path
before importing it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
