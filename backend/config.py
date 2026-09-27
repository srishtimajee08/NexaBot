"""Shared paths and embedding settings for ingestion and retrieval."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
KNOWLEDGE_BASE_DIR = PROJECT_DIR / "docs" / "knowledge_base"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"


def create_embeddings(local_files_only=False):
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        # The model is downloaded during ingestion. Runtime queries should use
        # the local cache and not fail because Hugging Face is temporarily offline.
        model_kwargs={"device": "cpu", "local_files_only": local_files_only},
        encode_kwargs={"normalize_embeddings": True},
    )
