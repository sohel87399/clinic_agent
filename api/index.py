"""
Vercel serverless entry point.
"""

import sys
import os

# Add project root to path so all local imports resolve on Vercel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Vercel sets env vars directly — no .env file needed in production
# But load it anyway for local testing
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"), override=False)
except Exception:
    pass

from server import app  # noqa: F401
