# nexaBot — Customer Support RAG Chatbot

A Flask and LangChain support chatbot for the fictional NexaCart company, with a vanilla HTML/CSS/JavaScript frontend and Groq generation.

## Easiest hosting: one Render service

Follow [the beginner hosting guide](docs/SIMPLE_HOSTING.md): extract the ZIP, upload its contents to a private GitHub repository, connect it as a Render Blueprint, and enter your Groq key. Render runs the website and Python chatbot together at one HTTPS address. The template selects the **Free instance** (512 MB); the embedding runtime may exceed this limit. Use Render New > Web Service and choose Free if Blueprint creation asks for a card. Do not approve paid resources. No service has been created yet.

Netlify is not needed for this version. The Docker build installs dependencies, downloads embeddings, and builds FAISS automatically. Keep `BACKEND_API_TOKEN` unset so the browser can call Flask directly.

## Project layout

```text
nexaBot/
├── backend/
│   ├── __init__.py
│   ├── app.py                 Flask API
│   ├── rag.py                 Retrieval and Groq generation
│   ├── ingest.py              Document ingestion
│   ├── config.py              Shared paths and model settings
│   ├── requirements.txt
│   ├── .env.example           Copy to .env and enter your own key
│   ├── tests/test_project.py
│   └── vector_store/          Saved FAISS index
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── docs/
│   ├── PROJECT_GUIDE.md       Architecture, setup, troubleshooting and viva
│   ├── SIMPLE_HOSTING.md     Beginner single-host deployment
│   └── knowledge_base/       Company support TXT/PDF documents
├── Dockerfile               Website + Python chatbot container
├── render.yaml              Single-service hosting template
├── .gitignore
└── README.md
```

## Setup and run

Use [single-host deployment](docs/SIMPLE_HOSTING.md) for the simplest public setup. The workspace also retains the older optional Netlify proxy files, but they are not required and are excluded from the simple-hosting ZIP. The new Render address replaces the need for the old Netlify address.

The instructions below run the project locally.

Run these commands from the project root, not from inside `backend/`.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

For a new setup, enter your Groq key in `backend/.env`. Do not overwrite an existing configured `.env`. The existing workspace key and index have already been moved to `backend/`.

```powershell
python -m backend.ingest
python -m backend.app
```

Open http://127.0.0.1:5000. Ingestion is needed only for a new index or changed documents. The folder reorganization does not require rebuilding the existing index.

With this workspace's existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m backend.app
```

## Checks

```powershell
python -m unittest discover -s backend/tests -v
node --check frontend/script.js
```

Node is optional and only needed for the JavaScript syntax check above. Flask serves `frontend/` through `/static/`, and the frontend calls `/api/chat` on the same host. Source metadata remains in the Python API for grounding; citations are hidden in the customer interface.

See [the complete project guide](docs/PROJECT_GUIDE.md) for architecture, installation on other platforms, and the technical summary for your viva.
