"""
Entry point kept at the repo root so `uvicorn main:app --reload` still works
exactly as before. The actual app now lives in app/main.py, split into
routers under app/routers/.
"""
from app.main import app  # noqa: F401  (re-exported for `uvicorn main:app`)
