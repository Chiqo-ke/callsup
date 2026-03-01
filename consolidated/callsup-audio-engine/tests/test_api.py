from app.config import Settings
from app.main import create_app


def test_ingest_and_get_transcript_flow(client):
    response = client.post(
        "/audio/ingest",
        data={"business_id": "biz-1", "conv_id": "conv-1"},
        files={"file": ("sample.wav", b"hello customer at me@example.com", "audio/wav")},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"

    transcript_response = client.get("/audio/transcript/conv-1")
    assert transcript_response.status_code == 200
    body = transcript_response.json()
    assert isinstance(body, list)
    assert body
    assert body[0]["business_id"] == "biz-1"
    assert body[0]["conv_id"] == "conv-1"
    assert "segment_id" in body[0]
    assert "start_ts" in body[0]
    assert "end_ts" in body[0]
    assert "[REDACTED_EMAIL]" in body[0]["text"]


def test_get_transcript_not_found(client):
    response = client.get("/audio/transcript/missing-conv")
    assert response.status_code == 404


def test_tls_enforcement_blocks_plain_http():
    app = create_app(
        Settings(
            enforce_tls_in_transit=True,
            allow_insecure_http=False,
            encryption_key="hEKxY8Q_9l8UlDc6HBs2jJm8UhjKxB95idQ2YG9kgSc=",
        )
    )
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 400

