import sys
from pathlib import Path

# Add repository root to python module path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app

# Expose app for Vercel Serverless Function runtime
__all__ = ["app"]
