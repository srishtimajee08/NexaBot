"""Small Flask API; run from the project root with python -m backend.app."""
import hmac
import os

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from .config import FRONTEND_DIR, VECTOR_STORE_DIR
from .rag import SetupError, answer_question

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.post("/api/chat")
def chat():
    expected_token = os.getenv("BACKEND_API_TOKEN", "").strip()
    if os.getenv("REQUIRE_BACKEND_TOKEN") == "1" and not expected_token:
        return jsonify(error="The support service is not configured yet."), 503
    if expected_token and not hmac.compare_digest(
        request.headers.get("X-Backend-Token", "").encode("utf-8"), expected_token.encode("utf-8")
    ):
        return jsonify(error="Unauthorized request."), 401
    if not request.is_json:
        return jsonify(error="Send a JSON request with a message field."), 415
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get("message"), str):
        return jsonify(error="The message field must be text."), 400
    message = data["message"].strip()
    if not message:
        return jsonify(error="Please enter a question."), 400
    if len(message) > 2000:
        return jsonify(error="Please keep your question under 2,000 characters."), 400
    try:
        return jsonify(answer_question(message))
    except SetupError as error:
        return jsonify(error=str(error)), 503
    except Exception as error:
        # Keep the browser message generic, but leave a safe diagnostic in the terminal.
        provider_error = getattr(error, "body", None)
        provider_code = None
        if isinstance(provider_error, dict):
            detail = provider_error.get("error", provider_error)
            if isinstance(detail, dict):
                provider_code = detail.get("code") or detail.get("type")
        app.logger.error(
            "Chat request failed: %s%s%s",
            type(error).__name__,
            f" (provider={provider_code})" if provider_code else "",
            f"; cause={type(error.__cause__).__name__}" if error.__cause__ else "",
        )
        if type(error).__name__ in {"APIConnectionError", "APITimeoutError", "ConnectError"}:
            return jsonify(
                error="The support service cannot reach Groq right now. Please try again shortly."
            ), 503
        return jsonify(error="The assistant couldn't respond right now. Please try again shortly."), 502


@app.errorhandler(BadRequest)
def invalid_json(error):
    return jsonify(error="The request contains invalid JSON."), 400


@app.get("/api/health")
def health():
    indexed = all((VECTOR_STORE_DIR / name).is_file() for name in ["index.faiss", "index.pkl", "metadata.json"])
    return jsonify(status="ok" if indexed else "not_ready"), 200 if indexed else 503


@app.errorhandler(RequestEntityTooLarge)
def too_large(error):
    return jsonify(error="The request is too large. Please send a shorter question."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
