import os
import sys

# ------------------------------------------------------------------------------
# Set up sys.path:
#
# Our project structure is assumed to be:
#
#   dasp-wikirag/
#       rag_retriever_service/
#           src/
#               core/
#                   app.py
#               ... (other modules)
#           tests/
#               test_core.py   <-- THIS FILE
#
# Since we run tests from the repository root (dasp-wikirag),
# we need to insert the repository root into sys.path.
#
# The repository root is two levels up from this file.
# ------------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, repo_root)

# (Optional: Uncomment the next line to debug sys.path)
# print("Repository root added to sys.path:", repo_root)

# ------------------------------------------------------------------------------
# Monkey-patch chromadb.HttpClient to avoid connecting to a real Chroma server.
# This patch must occur before importing any modules from app.py.
# ------------------------------------------------------------------------------
import chromadb

class FakeChromaCollection:
    def count(self):
        # Return a dummy count so that any call to .count() works.
        return 2

    def get(self):
        # Mimic the expected return structure.
        # The app expects a dict with a key "metadatas" that is a list.
        return {"metadatas": [{"collection_name": "WikiData", "model": "dummy_model"}]}

class FakeChromaClient:
    def __init__(self, *args, **kwargs):
        pass

    def get_collection(self, name):
        # Provide a fake collection for get_collection()
        return FakeChromaCollection()

    def get_or_create_collection(self, name):
        return FakeChromaCollection()

    def get_user_identity(self):
        return {}

# Replace chromadb's HttpClient with our fake version.
chromadb.HttpClient = FakeChromaClient

# ------------------------------------------------------------------------------
# Monkey-patch the built-in open so that when "rag_prompt_template.txt" is read,
# a dummy template is provided (avoiding a FileNotFoundError).
# This patch must occur before importing app.py.
# ------------------------------------------------------------------------------
import os
import io
import builtins

_original_open = builtins.open

# Compute the expected absolute path for the template file in the test.
# Assuming test_core.py is located in rag_retriever_service/tests,
# this will resolve to: <repo-root>/rag_retriever_service/src/prompts/rag_prompt_template.txt
expected_template_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "src", "prompts", "rag_prompt_template.txt"
)
expected_template_path = os.path.abspath(expected_template_path)

def fake_open(filename, mode='r', *args, **kwargs):
    # Compare the absolute path of the file being opened with the expected template path.
    if os.path.abspath(filename) == expected_template_path:
        dummy_template = "Dummy template with query: {{ query }} and context: {{ context }}"
        return io.StringIO(dummy_template)
    return _original_open(filename, mode, *args, **kwargs)

builtins.open = fake_open

# ------------------------------------------------------------------------------
# Monkey-patch HuggingFaceEmbedding to bypass model downloading.
# This must occur before the application module is imported.
# ------------------------------------------------------------------------------
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

def dummy_init(self, model_name):
    # Bypass pydantic's __setattr__ by using object.__setattr__
    object.__setattr__(self, '__pydantic_fields_set__', set())
    object.__setattr__(self, 'model_name', model_name)
    # Set additional dummy attributes required by the application.
    object.__setattr__(self, 'transformer_model', None)
    object.__setattr__(self, 'tokenizer', None)

HuggingFaceEmbedding.__init__ = dummy_init

# ------------------------------------------------------------------------------
# Now import the application modules.
#
# With the repository root inserted into sys.path, we can import the app using its
# full absolute path. Note that since our code is in:
#
#   dasp-wikirag/rag_retriever_service/src/core/app.py
#
# we import using:
#
#   from rag_retriever_service.src.core.app import app, index, cross_encoder
# ------------------------------------------------------------------------------
import json
import pytest
from fastapi.testclient import TestClient

from rag_retriever_service.src.core.app import app, index, cross_encoder

# ------------------------------------------------------------------------------
# Dummy classes to simulate retrieval behavior.
# ------------------------------------------------------------------------------
class DummyNode:
    """
    A dummy node simulating a retrieved document/chunk.
    Includes a default 'chunk_header' in metadata so that the app code
    (which accesses node.metadata["chunk_header"]) works without error.
    """
    def __init__(self, content: str, path: str, chunk_header: str = "dummy_header"):
        self._content = content
        self.metadata = {"path": path, "chunk_header": chunk_header}

    def get_content(self) -> str:
        return self._content

class FakeRetriever:
    """A fake retriever that always returns the same preset dummy nodes."""
    def __init__(self, nodes):
        self.nodes = nodes

    def retrieve(self, query: str):
        # Always return the same dummy nodes irrespective of the query.
        return self.nodes

# ------------------------------------------------------------------------------
# Pytest fixtures to override external dependencies.
# ------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def override_index_retriever(monkeypatch):
    """
    Override index.as_retriever so that it returns a FakeRetriever with two dummy nodes.
    """
    def fake_as_retriever(similarity_top_k, filters):
        dummy_nodes = [
            DummyNode("Dummy content 1", "/dummy/path/1"),
            DummyNode("Dummy content 2", "/dummy/path/2")
        ]
        return FakeRetriever(dummy_nodes)
    monkeypatch.setattr(index, "as_retriever", fake_as_retriever)

@pytest.fixture(autouse=True)
def override_cross_encoder_predict(monkeypatch):
    """
    Override cross_encoder.predict so that it returns fixed scores for deterministic re-ranking.
    """
    def fake_predict(query_chunk_pairs):
        # Return fixed scores corresponding to each dummy node.
        return [0.95, 0.50]
    monkeypatch.setattr(cross_encoder, "predict", fake_predict)

@pytest.fixture
def client():
    """Return a TestClient instance for the FastAPI app."""
    return TestClient(app)

# ------------------------------------------------------------------------------
# Actual test for the /retrieve_chunks endpoint.
# ------------------------------------------------------------------------------
def test_retrieve_chunks_success(client):
    """
    Test that the /retrieve_chunks endpoint returns a final payload with status 'success'
    and the expected keys. This test uses the monkey-patched retriever and cross-encoder.
    """
    response = client.get(
        "/retrieve_chunks",
        params={"query": "test query", "jwt_token": "dummy_token"}
    )
    
    # Collect the streaming response data.
    data = ""
    for chunk in response.iter_text():
        data += chunk

    # SSE events are separated by double newlines.
    events = [event for event in data.split("\n\n") if event.startswith("data:")]

    # Look for the final JSON payload that contains the "status" key.
    final_payload = None
    for event in events:
        payload_str = event[len("data:"):].strip()
        if payload_str.startswith("{"):
            try:
                payload = json.loads(payload_str)
                if isinstance(payload, dict) and "status" in payload:
                    final_payload = payload
            except json.JSONDecodeError:
                continue

    assert final_payload is not None, "Final payload not found in the streaming response"
    assert final_payload.get("status") == "success"
    assert "rag_prompt" in final_payload
    assert "sources" in final_payload
    assert isinstance(final_payload["sources"], list)
    # Expect two sources, matching the two dummy nodes.
    assert len(final_payload["sources"]) == 2