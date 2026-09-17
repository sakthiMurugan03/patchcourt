"""Tests for the /api/baseline/* endpoints."""
import json

import pytest
from fastapi.testclient import TestClient

from patchcourt.agents.schemas import Claim, Evidence, ReviewReport


def _fake_report() -> ReviewReport:
    return ReviewReport(
        pr_url="https://github.com/a/b/pull/42",
        overall_score=8.5,
        verdict="BLOCK",
        claims=[
            Claim(
                agent="tools",
                issue="possible SQL injection",
                file="app.py",
                line=10,
                severity=4,
                evidence=[Evidence(tier=1, text="[semgrep] detect")],
                confidence=0.9,
                tier=1,
                corroborated=True,
                source="tool",
            ),
            Claim(
                agent="llm",
                issue="unused import",
                file="helper.py",
                line=5,
                severity=2,
                evidence=[Evidence(tier=5, text="llm guess")],
                confidence=0.3,
                tier=5,
                source="llm",
            ),
        ],
        debate_transcripts=[],
    )


class _FakeSonarIssues:
    def __init__(self):
        self.count = 0

    def __call__(self, url, **kwargs):
        self.count += 1
        if "/api/issues/search" in url:
            return _FakeResp(
                {
                    "paging": {"total": 2, "pageIndex": 1, "pageSize": 100},
                    "issues": [
                        {
                            "component": "patchcourt:app.py",
                            "textRange": {"startLine": 10},
                            "severity": "CRITICAL",
                            "type": "VULNERABILITY",
                            "rule": "security:SQLInjection",
                            "message": "SQL injection risk",
                        },
                        {
                            "component": "patchcourt:other.py",
                            "textRange": {"startLine": 99},
                            "severity": "MINOR",
                            "type": "CODE_SMELL",
                            "rule": "py:S123",
                            "message": "minor issue",
                        },
                    ],
                }
            )
        if "pulls/42/files" in url:
            return _FakeResp([{"filename": "app.py"}])
        raise AssertionError(f"unexpected url {url}")


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def _fake_parse(_url):
    return ("a", "b", 42)


def test_baseline_latest_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "patchcourt.baseline.sonarqube_baseline._reports_dir", lambda: tmp_path
    )
    from patchcourt.api.app import app

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/baseline/latest")
        assert resp.status_code == 404
        assert "No baseline report saved yet" in resp.json()["detail"]


def test_baseline_latest_returns_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "patchcourt.baseline.sonarqube_baseline._reports_dir", lambda: tmp_path
    )
    payload = {
        "generated_at": "2026-09-17T00:00:00Z",
        "pr_url": "https://github.com/a/b/pull/1",
        "component": "a:b",
        "server_url": "http://localhost:9000",
        "total_open_issues": 3,
        "issues_touching_pr": 2,
        "summary": {"vulnerabilities": 1, "bugs": 0, "code_smells": 2},
        "issues": [
            {
                "file": "app.py",
                "line": 10,
                "severity": "CRITICAL",
                "type": "VULNERABILITY",
                "rule": "security:SQL",
                "message": "SQL injection",
                "in_pr": True,
                "suggested_tier": 1,
            }
        ],
    }
    (tmp_path / "baseline-a-b-1-20260917T000000Z.json").write_text(json.dumps(payload))

    from patchcourt.api.app import app

    with TestClient(app) as c:
        resp = c.get("/api/baseline/latest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["pr_url"] == "https://github.com/a/b/pull/1"
        assert body["issues_touching_pr"] == 2


def test_baseline_compare_invalid_url(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "patchcourt.baseline.sonarqube_baseline._reports_dir", lambda: tmp_path
    )
    from patchcourt.api.app import app

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.post("/api/baseline", json={"pr_url": "https://evil.com/x/pull/1"})
        assert resp.status_code == 400
        assert "Not a valid GitHub PR URL" in resp.json()["detail"]


def test_baseline_compare_full(tmp_path, monkeypatch):
    from patchcourt.config import settings

    monkeypatch.setattr(settings, "sonar_token", "t")
    monkeypatch.setattr(
        "patchcourt.baseline.sonarqube_baseline._reports_dir", lambda: tmp_path
    )
    monkeypatch.setattr("patchcourt.baseline.sonarqube_baseline.parse_pr_url", _fake_parse)
    monkeypatch.setattr("patchcourt.baseline.sonarqube_baseline.httpx.get", _FakeSonarIssues())

    async def _fake_review(pr_url, **_kw):
        return _fake_report()

    import importlib

    _api_module = importlib.import_module("patchcourt.api.app")
    monkeypatch.setattr(_api_module, "run_review", _fake_review)

    from patchcourt.api.app import app

    with TestClient(app) as c:
        resp = c.post("/api/baseline", json={"pr_url": "https://github.com/a/b/pull/42"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["component"] == "patchcourt"
        assert body["issues_touching_pr"] == 1
        assert "patchcourt" in body
        pc = body["patchcourt"]
        assert pc["verdict"] == "BLOCK"
        comp = pc["comparison"]
        assert comp["counts"]["raw"] == 1
        assert comp["counts"]["confirmed"] == 1
        assert comp["counts"]["suppressed"] == 0
        assert comp["counts"]["sonar_missed"] == 0
        assert len(comp["confirmed"]) == 1
        assert comp["confirmed"][0]["rule"] == "security:SQLInjection"
