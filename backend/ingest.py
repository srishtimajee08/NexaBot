"""Run after changing company documents: python -m backend.ingest."""
import json
import sys

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import EMBEDDING_MODEL, KNOWLEDGE_BASE_DIR, VECTOR_STORE_DIR, create_embeddings


def load_documents():
    if not KNOWLEDGE_BASE_DIR.is_dir():
        raise ValueError("Create docs/knowledge_base/ and add TXT or text-based PDF files first.")
    documents = []
    for path in sorted(KNOWLEDGE_BASE_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".pdf"}:
            continue
        print(f"  Loading {path.name}")
        loader = PyPDFLoader(str(path)) if path.suffix.lower() == ".pdf" else TextLoader(str(path), encoding="utf-8")
        try:
            pages = loader.load()
        except Exception as error:
            raise ValueError(f"Could not read {path.name}. Check its format and encoding.") from error
        for page in pages:
            page.metadata["source"] = path.name
            if page.page_content.strip():
                documents.append(page)
    if not documents:
        raise ValueError("No readable text found. Add UTF-8 TXT files or PDFs with selectable text; scanned PDFs need OCR first.")
    return documents


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=180)
    return splitter.split_documents(documents)


def create_vector_store(chunks):
    embeddings = create_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTOR_STORE_DIR))
    (VECTOR_STORE_DIR / "metadata.json").write_text(
        json.dumps({"embedding_model": EMBEDDING_MODEL, "chunks": len(chunks)}, indent=2), encoding="utf-8"
    )
    return vectorstore


def main():
    try:
        print("Loading documents...")
        documents = load_documents()
        print(f"Loaded {len(documents)} documents/pages.")
        chunks = split_documents(documents)
        print(f"Created {len(chunks)} chunks.")
        print("Generating embeddings (the first run downloads the model)...")
        create_vector_store(chunks)
        print("FAISS vector store created successfully. Start or restart python -m backend.app.")
    except Exception as error:
        print(f"Ingestion failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
