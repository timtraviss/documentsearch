import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    os.environ.setdefault("PDF_FOLDER", "/tmp")
    os.environ.setdefault("DB_PATH", os.path.join(
        os.path.dirname(__file__), "..", "backend", "search.db"
    ))
    import backend.app as app_module
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_ask_empty_query(client):
    res = client.post("/ask",
                      data='{"query": ""}',
                      content_type="application/json")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_ask_no_embeddings(client):
    import backend.app as app_module
    with patch.object(app_module, "HAS_EMBEDDINGS", False):
        res = client.post("/ask",
                          data='{"query": "test"}',
                          content_type="application/json")
    assert res.status_code == 503
    data = res.get_json()
    assert "error" in data
    assert "embeddings" in data["error"].lower()


def test_ask_missing_api_key(client):
    import backend.app as app_module
    mock_chunks = [{"path": "test.pdf", "filename": "test.pdf", "snippet": "some text"}]
    with patch.object(app_module, "HAS_EMBEDDINGS", True), \
         patch.object(app_module, "search_chunks", return_value=mock_chunks), \
         patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
        res = client.post("/ask",
                          data='{"query": "test"}',
                          content_type="application/json")
    assert res.status_code == 503


def test_ask_returns_answer_and_sources(client):
    import backend.app as app_module
    mock_chunks = [
        {"path": "contract.pdf", "filename": "contract.pdf",
         "snippet": "The notice period is 90 days."},
        {"path": "contract.pdf", "filename": "contract.pdf",
         "snippet": "Liability is capped at 3 months fees."},
    ]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="The notice period is 90 days.")]

    with patch.object(app_module, "HAS_EMBEDDINGS", True), \
         patch.object(app_module, "search_chunks", return_value=mock_chunks), \
         patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
         patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        res = client.post(
            "/ask",
            data='{"query": "What is the notice period?", "messages": []}',
            content_type="application/json",
        )

    assert res.status_code == 200
    data = res.get_json()
    assert data["answer"] == "The notice period is 90 days."
    # Two chunks from same doc → one deduplicated source
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "contract.pdf"


def test_ask_passes_conversation_history(client):
    import backend.app as app_module
    import json
    mock_chunks = [{"path": "a.pdf", "filename": "a.pdf", "snippet": "context"}]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Follow-up answer.")]

    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
    ]

    with patch.object(app_module, "HAS_EMBEDDINGS", True), \
         patch.object(app_module, "search_chunks", return_value=mock_chunks), \
         patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
         patch("anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        res = client.post(
            "/ask",
            data=json.dumps({"query": "follow up", "messages": history}),
            content_type="application/json",
        )

    assert res.status_code == 200
    call_kwargs = mock_cls.return_value.messages.create.call_args[1]
    messages_sent = call_kwargs["messages"]
    assert messages_sent[0]["role"] == "user"
    assert messages_sent[0]["content"] == "First question"
    assert messages_sent[1]["role"] == "assistant"
    assert messages_sent[-1]["role"] == "user"


def test_rebuild_embeddings_starts(client):
    import backend.app as app_module
    app_module.rebuild_status["running"] = False
    res = client.post("/rebuild-embeddings", content_type="application/json")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"
    import time; time.sleep(0.05)
    app_module.rebuild_status["running"] = False


def test_rebuild_embeddings_already_running(client):
    import backend.app as app_module
    app_module.rebuild_status["running"] = True
    try:
        res = client.post("/rebuild-embeddings", content_type="application/json")
        assert res.status_code == 409
    finally:
        app_module.rebuild_status["running"] = False


def test_rebuild_embeddings_status_shape(client):
    res = client.get("/rebuild-embeddings/status")
    assert res.status_code == 200
    data = res.get_json()
    assert "running" in data
    assert "logs" in data
    assert "count" in data
    assert "error" in data
