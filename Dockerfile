FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-deploy.txt backend/
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r backend/requirements-deploy.txt

COPY backend/ backend/
COPY docs/knowledge_base/ docs/knowledge_base/
COPY frontend/ frontend/
# Download the embedding model and build FAISS once, without a Groq API key.
RUN python -m backend.ingest \
    && useradd --create-home --uid 10001 chatbot \
    && chown -R chatbot:chatbot /app /opt/huggingface

ENV HF_HUB_OFFLINE=1 \
    REQUIRE_BACKEND_TOKEN=0 \
    GROQ_TIMEOUT_SECONDS=40 \
    PRELOAD_RAG=1 \
    PORT=8000

USER chatbot
EXPOSE 8000
CMD ["gunicorn", "--config", "backend/gunicorn.conf.py", "backend.wsgi:app"]
