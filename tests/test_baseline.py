"""SonarQube baseline module — HTTP is mocked so tests run offline."""
import json

import httpx
import pytest

from patchcourt.baseline import build_report, markdown, parse_pr_url, write_report
from patchcourt.config import settings


def _fake_issues_json():
    return {
        "paging": {"total": 2, "pageIndex": 1, "pageSize": 100},
        "issues": [
            {
                "component": "patchcourt:app/main.py",
                "textRange": {"startLine": 41},
                "severity": "CRITICAL",
                "type": "VULNERABILITY",
                "rule": "security:CommandExecution",
                "message": "Command execution found",
            },
            {
                "component": "patchcourt:lib/helper.py",
                "textRange": {"startLine": 3},
                "severity": "MINOR",
                "type": "CODE_SMELL",
                "rule": "python:S12",
                "message": "unused parameter",
            },
        ],
    }


class _FakeResp:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


def test_parse_pr_url():
    assert parse_pr_url("https://github.com/acme/server/pull/77") == ("acme", "server", 77)
    with pytest.raises(ValueError):
        parse_pr_url("https://example.com/nope")


def test_build_report(monkeypatch):
    monkeypatch.setattr(settings, "sonar_component", "patchcourt")
    monkeypatch.setattr(settings, "sonar_token", "fake-token")

    calls = {"issues": 0, "pr": 0}

    def fake_get(url, **kwargs):
        if "/api/issues/search" in url:
            calls["issues"] += 1
            return _FakeResp(_fake_issues_json())
        if "pulls/1/files" in url:
            calls["pr"] += 1
            return _FakeResp([{"filename": "app/main.py"}])
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr("patchcourt.baseline.sonarqube_baseline.httpx.get", fake_get)

    report = build_report("https://github.com/acme/server/pull/1")
    assert report["total_open_issues"] == 2
    assert report["issues_touching_pr"] == 1
    by_file = {r["file"]: r for r in report["issues"]}
    assert by_file["app/main.py"]["in_pr"] is True
    assert by_file["app/main.py"]["suggested_tier"] == 1  # CRITICAL → T1
    assert by_file["lib/helper.py"]["suggested_tier"] == 3  # MINOR → T3
    assert calls["issues"] == 1 and calls["pr"] == 1


def test_build_report_requires_token(monkeypatch):
    monkeypatch.setattr(settings, "sonar_token", "")
    with pytest.raises(ValueError, match="SONAR_TOKEN"):
        build_report("https://github.com/acme/server/pull/1")


def test_markdown_and_write(monkeypatch, tmp_path):
    from pathlib import Path

    monkeypatch.setattr("patchcourt.config.settings.sonar_token", "t")
    monkeypatch.setattr(
        "patchcourt.baseline.sonarqube_baseline.httpx.get", _fake_get_for(None)
    )
    monkeypatch.setattr(
        "patchcourt.baseline.sonarqube_baseline._reports_dir", lambda: tmp_path
    )

    report = build_report("https://github.com/acme/server/pull/1")
    md = markdown(report)
    assert "SonarQube baseline" in md
    assert "app/main.py" in md

    md_path, json_path = write_report("https://github.com/acme/server/pull/1", report)
    assert Path(md_path).exists() and Path(json_path).exists()
    assert "command execution found" in Path(md_path).read_text().lower()


def test_latest_report_picks_newest(monkeypatch, tmp_path):
    from pathlib import Path

    from patchcourt.baseline import latest_report

    monkeypatch.setattr(
        "patchcourt.baseline.sonarqube_baseline._reports_dir", lambda: tmp_path
    )
    assert latest_report() is None

    older = tmp_path / "baseline-a-b-1-20200101T000000Z.json"
    newer = tmp_path / "baseline-a-b-1-20200102T000000Z.json"
    newer.write_text('{"tag": "new"}')
    older.write_text('{"tag": "old"}')
    import os

    os.utime(older, (1_600_000_000, 1_600_000_000))
    os.utime(newer, (1_600_100_000, 1_600_100_000))
    assert latest_report() == {"tag": "new"}


def _fake_get_for(_base):
    def fake_get(url, **kwargs):
        if "/api/issues/search" in url:
            return _FakeResp(_fake_issues_json())
        if "pulls/1/files" in url:
            return _FakeResp([{"filename": "app/main.py"}])
        raise AssertionError(f"unexpected url {url}")

    return fake_get