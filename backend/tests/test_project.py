"""Offline API and grounding checks: python -m unittest discover -s backend/tests -v."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

from backend import app, ingest, rag


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_interface_and_assets(self):
        for path in ["/", "/static/style.css", "/static/script.js"]:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)

    @patch("backend.app.answer_question")
    def test_single_host_browser_chat(self, answer):
        answer.return_value = {"answer": "Documented answer", "sources": ["faq.txt"]}
        with patch.dict("os.environ", {"BACKEND_API_TOKEN": "", "REQUIRE_BACKEND_TOKEN": "0"}):
            for path in ["/", "/static/script.js"]:
                with self.client.get(path) as page:
                    self.assertEqual(page.status_code, 200)
            response = self.client.post("/api/chat", json={"message": "Refund policy?"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["answer"], "Documented answer")

    @patch("backend.app.answer_question")
    def test_hosted_backend_requires_shared_token(self, answer):
        answer.return_value = {"answer": "Documented answer", "sources": ["faq.txt"]}
        with patch.dict("os.environ", {"BACKEND_API_TOKEN": "test-only-token", "REQUIRE_BACKEND_TOKEN": "1"}):
            for headers in [{}, {"X-Backend-Token": "wrong-token"}]:
                response = self.client.post("/api/chat", json={"message": "Hello"}, headers=headers)
                self.assertEqual(response.status_code, 401)
            answer.assert_not_called()
            response = self.client.post("/api/chat", json={"message": "Hello"}, headers={"X-Backend-Token": "test-only-token"})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("test-only-token", response.get_data(as_text=True))

    @patch("backend.app.answer_question")
    def test_production_missing_token_fails_closed(self, answer):
        with patch.dict("os.environ", {"BACKEND_API_TOKEN": "", "REQUIRE_BACKEND_TOKEN": "1"}):
            self.assertEqual(self.client.post("/api/chat", json={"message": "Hello"}).status_code, 503)
            answer.assert_not_called()

    def test_health_checks_index_without_provider_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(app, "VECTOR_STORE_DIR", root):
                self.assertEqual(self.client.get("/api/health").status_code, 503)
                for name in ["index.faiss", "index.pkl", "metadata.json"]:
                    (root / name).touch()
                self.assertEqual(self.client.get("/api/health").json, {"status": "ok"})

    def test_bad_inputs(self):
        for data in [{}, [], {"message": None}, {"message": 1}, {"message": "  "}, {"message": "x" * 2001}]:
            self.assertEqual(self.client.post("/api/chat", json=data).status_code, 400)
        self.assertEqual(self.client.post("/api/chat", data="hello").status_code, 415)
        self.assertEqual(self.client.post("/api/chat", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/chat", json={"message": "x" * 20000}).status_code, 413)

    @patch("backend.app.answer_question")
    def test_chat_contract(self, answer):
        answer.return_value = {"answer": "A grounded response", "sources": ["faq.txt"]}
        result = self.client.post("/api/chat", json={"message": "  A question  "})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json, answer.return_value)
        answer.assert_called_once_with("A question")

    @patch("backend.app.answer_question")
    def test_errors_do_not_leak(self, answer):
        answer.side_effect = RuntimeError("secret-provider-details")
        response = self.client.post("/api/chat", json={"message": "Hello"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("secret", response.get_data(as_text=True))
        answer.side_effect = rag.SetupError("Run python ingest.py")
        self.assertEqual(self.client.post("/api/chat", json={"message": "Hello"}).status_code, 503)


class RagTests(unittest.TestCase):
    def test_reasoning_options_are_model_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["index.faiss", "index.pkl"]:
                (root / name).touch()
            (root / "metadata.json").write_text(json.dumps({"embedding_model": rag.EMBEDDING_MODEL}))
            for model in ["qwen/qwen3-32b", "another-model"]:
                rag.load_rag_resources.cache_clear()
                with patch.dict("os.environ", {"GROQ_API_KEY": "test-only", "GROQ_MODEL": model}), \
                     patch.object(rag, "VECTOR_STORE_DIR", root), \
                     patch("backend.rag.create_embeddings"), patch("backend.rag.FAISS.load_local"), \
                     patch("backend.rag.ChatGroq") as chat_model:
                    rag.load_rag_resources()
                    options = chat_model.call_args.kwargs
                    self.assertEqual(options["model_kwargs"]["response_format"], {"type": "json_object"})
                    if model.startswith("qwen/"):
                        self.assertEqual(options["reasoning_effort"], "none")
                        self.assertEqual(options["reasoning_format"], "hidden")
                    else:
                        self.assertNotIn("reasoning_effort", options)
                rag.load_rag_resources.cache_clear()

    def test_reasoning_wrapped_output_is_logged_without_disclosure(self):
        with self.assertLogs("backend.rag", level="WARNING") as logs:
            result, _ = self.run_answer('<think>private reasoning</think>{"answer":"text","source_ids":[1]}')
        self.assertEqual(result["answer"], rag.FALLBACK)
        self.assertNotIn("private reasoning", " ".join(logs.output))

    def run_answer(self, content, documents=None):
        if documents is None:
            documents = [Document(page_content="Policy", metadata={"source": "faq.txt"})] * 2
        retriever = Mock()
        retriever.invoke.return_value = documents
        llm = Mock()
        llm.invoke.return_value = SimpleNamespace(content=content)
        with patch("backend.rag.load_rag_resources", return_value=(retriever, llm)):
            result = rag.answer_question("A question")
        return result, llm

    def test_sources_are_deduplicated(self):
        result, llm = self.run_answer(json.dumps({"answer": "An answer", "source_ids": [1, 2, 1]}))
        self.assertEqual(result["sources"], ["faq.txt"])
        self.assertIn("Company context", llm.invoke.call_args.args[0][1][1])

    def test_unsupported_and_invalid_output_fail_closed(self):
        outputs = ['not json', '[]', '{}', '{"answer":"unknown","source_ids":[]}',
                   '{"answer":"invented","source_ids":[99]}', '{"answer":"invented","source_ids":[true]}']
        for output in outputs:
            result, _ = self.run_answer(output)
            self.assertEqual(result, {"answer": rag.FALLBACK, "sources": []})
        result, llm = self.run_answer("unused", documents=[])
        self.assertEqual(result["answer"], rag.FALLBACK)
        llm.invoke.assert_not_called()

    def test_missing_api_key(self):
        rag.load_rag_resources.cache_clear()
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}):
            with self.assertRaises(rag.SetupError):
                rag.load_rag_resources()

    def test_txt_pdf_loaders_and_splitting(self):
        from pypdf import PdfWriter
        from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "policy.TXT").write_text("Return policy. " * 200, encoding="utf-8")
            (root / "skip.csv").write_text("unsupported", encoding="utf-8")
            writer = PdfWriter()
            page = writer.add_blank_page(width=200, height=200)
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                     NameObject('/Subtype'): NameObject('/Type1'),
                                     NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({
                NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
            stream = DecodedStreamObject()
            stream.set_data(b'BT /F1 12 Tf 10 100 Td (PDF shipping instructions) Tj ET')
            page[NameObject('/Contents')] = stream
            with (root / "shipping.pdf").open("wb") as output:
                writer.write(output)
            with patch.object(ingest, "KNOWLEDGE_BASE_DIR", root):
                documents = ingest.load_documents()
            chunks = ingest.split_documents(documents)
            self.assertGreater(len(chunks), 1)
            self.assertEqual({chunk.metadata["source"] for chunk in chunks}, {"policy.TXT", "shipping.pdf"})
            pdf_document = next(doc for doc in documents if doc.metadata["source"] == "shipping.pdf")
            self.assertIn("PDF shipping instructions", pdf_document.page_content)
            self.assertEqual(pdf_document.metadata["page"], 0)
            self.assertTrue(all(len(chunk.page_content) <= 900 for chunk in chunks))

    def test_real_faiss_save_load_retrieve(self):
        # Deterministic tiny embeddings test storage without downloading a model.
        class TestEmbeddings(Embeddings):
            def embed_documents(self, texts):
                return [self.embed_query(text) for text in texts]

            def embed_query(self, text):
                return [1.0, 0.0] if "refund" in text else [0.0, 1.0]

        with tempfile.TemporaryDirectory() as directory:
            embeddings = TestEmbeddings()
            store = FAISS.from_documents([
                Document(page_content="refund policy", metadata={"source": "refund.txt"}),
                Document(page_content="shipping policy", metadata={"source": "shipping.txt"}),
            ], embeddings)
            store.save_local(directory)
            loaded = FAISS.load_local(directory, embeddings, allow_dangerous_deserialization=True)
            result = loaded.as_retriever(search_kwargs={"k": 1}).invoke("refund")
            self.assertEqual(result[0].metadata["source"], "refund.txt")


if __name__ == "__main__":
    unittest.main()
