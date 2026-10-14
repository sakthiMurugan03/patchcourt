"""Tests for the GitHub webhook integration."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from patchcourt.api import github_webhook as gh
from patchcourt.api.app import app
from patchcourt.config import settings

PR_URL = "https://github.com/acme/widgets/pull/7"
SECRET = "top-secret"


class FakeAssessment:
    file = "app.py"
    line = 42
    message = "Possible SQL injection"
    category = "security"
    contextual_action = "block"


class FakeReport:
    pr_url = PR_URL
    verdict = "BLOCK"
    overall_score = 12.5
    contextual_summary = {
        "total": 3,
        "blocking": 1,
        "by_action": {"block": 1, "remediate": 2},
    }
    finding_assessments = [FakeAssessment()]


def sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", SECRET)
    return SECRET


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------
def test_verify_signature_accepts_valid():
    body = b'{"hello": "world"}'
    assert gh.verify_signature(body, sign(body), SECRET) is True


def test_verify_signature_rejects_wrong_secret():
    body = b"{}"
    assert gh.verify_signature(body, sign(body, "other"), SECRET) is False


def test_verify_signature_rejects_missing_header():
    assert gh.verify_signature(b"{}", None, SECRET) is False


def test_verify_signature_rejects_bad_scheme():
    assert gh.verify_signature(b"{}", "sha1=deadbeef", SECRET) is False


def test_verify_signature_without_secret_is_false():
    assert gh.verify_signature(b"{}", "sha256=abc", "") is False


# ---------------------------------------------------------------------------
# Comment rendering
# ---------------------------------------------------------------------------
def test_build_verdict_comment_includes_key_details():
    comment = gh.build_verdict_comment(FakeReport())
    assert "BLOCK" in comment
    assert "12.5" in comment
    assert "app.py:42" in comment
    assert "Possible SQL injection" in comment
    assert "block" in comment


def test_build_verdict_comment_handles_empty_report():
    class Empty:
        verdict = "MERGE"
        overall_score = 0.0
        contextual_summary = {}
        finding_assessments = []

    comment = gh.build_verdict_comment(Empty())
    assert "MERGE" in comment


# ---------------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------------
def test_endpoint_503_without_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "")
    response = client.post("/api/webhooks/github", json={"action": "opened"})
    assert response.status_code == 503


def test_endpoint_401_on_bad_signature(client, webhook_secret):
    response = client.post(
        "/api/webhooks/github",
        content=b'{"action": "opened"}',
        headers={"x-hub-signature-256": "sha256=deadbeef", "x-github-event": "pull_request"},
    )
    assert response.status_code == 401


def test_endpoint_handles_ping(client, webhook_secret):
    body = b'{"zen": "keep it simple"}'
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={"x-hub-signature-256": sign(body), "x-github-event": "ping"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "event": "ping"}


def test_endpoint_ignores_unhandled_event(client, webhook_secret):
    body = json.dumps({"action": "opened"}).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={"x-hub-signature-256": sign(body), "x-github-event": "issues"},
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is False


def test_endpoint_ignores_unhandled_action(client, webhook_secret):
    body = json.dumps({"action": "closed", "pull_request": {"html_url": PR_URL}}).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={"x-hub-signature-256": sign(body), "x-github-event": "pull_request"},
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is False


def test_endpoint_requires_pr_url(client, webhook_secret):
    body = json.dumps({"action": "opened", "pull_request": {}}).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={"x-hub-signature-256": sign(body), "x-github-event": "pull_request"},
    )
    assert response.status_code == 400


def test_endpoint_schedules_review_and_returns_accepted(client, webhook_secret, monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(gh, "process_pull_request_event", seen.append)

    body = json.dumps(
        {"action": "opened", "pull_request": {"html_url": PR_URL}}
    ).encode()
    response = client.post(
        "/api/webhooks/github",
        content=body,
        headers={"x-hub-signature-256": sign(body), "x-github-event": "pull_request"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["pr_url"] == PR_URL
    assert seen == [PR_URL]


# ---------------------------------------------------------------------------
# Comment posting / processing
# ---------------------------------------------------------------------------
class FakeResponse:
    content = b'{"id": 1}'

    def raise_for_status(self):
        return None

    def json(self):
        return {"id": 1}


class FakeAsyncClient:
    def __init__(self):
        self.posted = None

    async def post(self, url, json=None, headers=None):
        self.posted = {"url": url, "json": json, "headers": headers}
        return FakeResponse()


async def test_post_pr_comment_uses_issues_endpoint():
    fake = FakeAsyncClient()
    result = await gh.post_pr_comment(PR_URL, "verdict body", client=fake)
    assert result == {"id": 1}
    assert fake.posted["url"] == "https://api.github.com/repos/acme/widgets/issues/7/comments"
    assert fake.posted["json"] == {"body": "verdict body"}


async def test_process_pull_request_event_posts_comment(monkeypatch):
    async def fake_run_review(pr_url: str):
        return FakeReport()

    monkeypatch.setattr("patchcourt.graph.run_review", fake_run_review)

    posted: dict[str, str] = {}

    async def fake_post(pr_url: str, body: str):
        posted["pr_url"] = pr_url
        posted["body"] = body

    monkeypatch.setattr(gh, "post_pr_comment", fake_post)

    result = await gh.process_pull_request_event(PR_URL)
    assert result["ok"] is True
    assert result["verdict"] == "BLOCK"
    assert posted["pr_url"] == PR_URL
    assert "PatchCourt verdict" in posted["body"]


async def test_process_pull_request_event_swallows_review_error(monkeypatch):
    async def boom(pr_url: str):
        raise RuntimeError("nope")

    monkeypatch.setattr("patchcourt.graph.run_review", boom)
    result = await gh.process_pull_request_event(PR_URL)
    assert result["ok"] is False
    assert result["stage"] == "review"
