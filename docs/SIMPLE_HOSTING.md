# Publish nexaBot on one host

The website and chatbot run together on Render. You get one HTTPS address for both. Flask serves the HTML, CSS, JavaScript, and `/api/chat`; Groq remains the LLM provider. No Netlify account, JavaScript backend, proxy token, or local Docker installation is needed.

## What you need

- A GitHub account and a Render account.
- Your own Groq API key, entered only in Render's secret settings.
- A hosting budget: `render.yaml` selects the **paid `1c-2g` (2 GB RAM)** plan for the Python embedding runtime. Review Render's displayed price before approving deployment. Preparing these files has not created a service or incurred hosting charges.

## Step 1 — Upload the extracted project to GitHub

1. Extract `nexaBot-simple-hosting.zip` on your computer.
2. On GitHub, create a new **private** repository, for example `nexabot`.
3. Choose **uploading an existing file** (or **Add file → Upload files**).
4. Upload the contents of the extracted `nexaBot` folder, including the `backend`, `frontend`, and `docs` folders. Upload the files, **not the ZIP itself**. Preserve the folder structure.
5. Commit the uploaded files. Check that `Dockerfile`, `.dockerignore`, and `render.yaml` appear at the repository root, alongside `README.md`.

The supplied ZIP excludes your real `.env`, virtual environment, and generated index. Never upload your local `.env`. Render rebuilds the index automatically.

## Step 2 — Create one Render service

1. Sign in at https://dashboard.render.com/.
2. Choose **New → Blueprint** and connect GitHub. Grant access to this repository.
3. Select your `nexabot` repository. Render reads the root `render.yaml` and shows one Docker web service.
4. Enter your `GROQ_API_KEY` when prompted. The configured model is `qwen/qwen3.8-27b`, previously tested with this project. If your account cannot access it, set `GROQ_MODEL` to a model available in your Groq console.
5. Review the paid plan and price, then choose **Deploy Blueprint** if you agree.
6. Wait for the service to become **Live**. The first build installs Python dependencies, downloads the embedding model, and creates FAISS automatically. You do not need to run `ingest.py` manually on Render.
7. Open the HTTPS address shown by Render, usually `https://<service-name>.onrender.com`.

Do not select Static Site. Do not add a build command or start command: the Dockerfile already specifies both. Leave the repository root directory blank. Do not add `BACKEND_URL` or `BACKEND_API_TOKEN`; they are unnecessary for this version. If reusing an older service, remove `BACKEND_API_TOKEN` and set `REQUIRE_BACKEND_TOKEN=0`.

## Step 3 — Try the chatbot

- Ask “What is your refund policy?” and check that a documented answer appears.
- Ask “Do you sell lifetime insurance?” and check that the assistant explains the information is unavailable.
- Open `/api/health` on your Render address: `{"status":"ok"}` means the index files exist. Test a chat question too, because health does not call Groq.

The interface is named nexaBot and does not display sources. The Python API retains citation metadata for debugging. Your old Netlify address does not change; share the new Render address with your evaluator.

## Updating documents

Edit files in `docs/knowledge_base/` and commit them to GitHub. Render rebuilds the image and its index on deployment. No separate database or persistent disk is required. Keep the embedding model setting consistent between ingestion and retrieval.

## If something fails

| Problem | What to check |
|---|---|
| Render cannot find configuration | `render.yaml` and `Dockerfile` must be at the repository root, not inside an extra `nexaBot` folder |
| Build fails downloading packages/model | Open Render's build logs and retry when the download service is reachable |
| Service exits or runs out of memory | Check Render logs and use the configured 2 GB plan or larger |
| Chat returns 401 | Remove the old `BACKEND_API_TOKEN` variable from Render |
| Groq authentication/model error | Check the secret key and model in Render's environment settings, then redeploy |
| Groq connection error | Inspect Render runtime logs; the hosted app uses Render's network, not your laptop's firewall |

This is a public demo chat endpoint. Requests can use your Groq allowance; check provider usage limits before sharing widely.

## Local use still works

Follow the root README. Hosting is optional; the original Flask and RAG workflow is unchanged.

## Verification limits

Offline tests check Flask routes, browser chat without a proxy token, document ingestion, FAISS persistence, and response validation. This workspace has no Docker installation, so the Linux container build and live Render deployment still need verification on the host. No hosting account has been provisioned automatically.

Official references: [Render Docker](https://render.com/docs/docker), [Render Blueprints](https://render.com/docs/infrastructure-as-code), [Blueprint settings](https://render.com/docs/blueprint-spec).
