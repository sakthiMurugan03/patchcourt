"""Tests for the SSE review stream endpoint."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from patchcourt.api import stream
from patchcourt.api.app import app


class FakeReport:
    pr_url = "https://github.com/acme/widgets/pull/7"
    verdict = "BLOCK"
    overall_score = 12.5
    contextual_summary = {"total": 2, "blocking": 1, "by_action": {"block": 1}}
    debate_transcripts = [
        {
            "file": "app.py",
            "issue": "SQL injection",
            "supporting": "unsanitised input",
            "opposing": "parameterised query used",
            "rounds": 2,
            "code_snippet": "cursor.execute(q)",
            "verdict_summary": "Fix the query",
        }
    ]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_resolve_pr_url_from_full_url():
    url = "https://github.com/acme/widgets/pull/7"
    assert stream.resolve_pr_url(url, None, None) == url


def test_resolve_pr_url_from_repo_and_number():
    assert (
        stream.resolve_pr_url("7", "acme/widgets", None)
        == "https://github.com/acme/widgets/pull/7"
    )


def test_resolve_pr_url_rejects_garbage():
    with pytest.raises(Exception):
        stream.resolve_pr_url("not-a-pr", None, None)


def test_sse_event_format():
    frame = stream.sse_event({"a": 1}, "status")
    assert frame.startswith("event: status\n")
    assert frame.endswith("\n\n")
    assert json.loads(frame.split("data: ", 1)[1].strip()) == {"a": 1}


def test_stream_endpoint_emits_events(client: TestClient, monkeypatch):
    async def fake_run_review(pr_url: str):
        return FakeReport()

    monkeypatch.setattr("patchcourt.graph.run_review", fake_run_review)

    response = client.get("/api/review/7/stream?repo=acme/widgets")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: status" in body
    assert "event: debate" in body
    assert "event: verdict" in body
    assert '"verdict": "BLOCK"' in body
    assert "event: done" in body


def test_stream_endpoint_emits_error_frame(client: TestClient, monkeypatch):
    async def boom(pr_url: str):
        raise RuntimeError("401 invalid api key")

    monkeypatch.setattr("patchcourt.graph.run_review", boom)

    response = client.get("/api/review/7/stream?repo=acme/widgets")
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "auth_failed" in response.text


def test_stream_endpoint_rejects_unresolvable_pr(client: TestClient):
    response = client.get("/api/review/nonsense/stream")
    assert response.status_code == 400
