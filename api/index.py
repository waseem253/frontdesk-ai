"""Vercel Python entrypoint — serves the ASGI `app`."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontdesk.main import app  # noqa: E402

__all__ = ["app"]
