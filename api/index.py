"""
Vercel serverless entry point — imports and re-exports the Flask app from server.py.
Vercel looks for a variable named `app` in this file.
"""

import sys
import os

# Make sure the project root is on the path so all local imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import app  # noqa: F401 — Vercel picks up `app` automatically
