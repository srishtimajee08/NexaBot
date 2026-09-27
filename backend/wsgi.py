"""Warm RAG resources during production startup before accepting requests."""
import os

from .app import app
from .rag import load_rag_resources

if os.getenv("REQUIRE_BACKEND_TOKEN") == "1" and not os.getenv("BACKEND_API_TOKEN", "").strip():
    raise RuntimeError("Set BACKEND_API_TOKEN before starting the production service.")

if os.getenv("PRELOAD_RAG") == "1":
    load_rag_resources()
