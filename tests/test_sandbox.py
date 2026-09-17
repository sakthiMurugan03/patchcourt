"""Sandbox runner behavior (graceful skip + parsing)."""
from patchcourt.sandbox import dedupe_findings, run_tools_in_sandbox
from patchcourt.sandbox.runner import _finding_from_dict
from patchcourt.tools import Finding
from patchcourt.config import settings


def test_finding_parse_from_sandbox_json():
    f = _finding_from_dict(
        {"tool": "semgrep", "file": "/workspace/app.py", "line": 7, "message": "injection", "severity": 5, "rule": "py.rule"}
    )
    assert f.tool == "semgrep"
    assert f.file == "app.py"  # leading slash stripped
    assert f.line == 7 and f.severity == 5


def test_dedupe_findings():
    fs = [
        Finding(tool="semgrep", file="a.py", line=1, message="x"),
        Finding(tool="semgrep", file="a.py", line=1, message="y"),
        Finding(tool="bandit", file="a.py", line=1, message="z"),
    ]
    out = dedupe_findings(fs)
    assert len(out) == 2  # semgrep a.py:1 appears twice


def test_sandbox_skipped_when_disabled():
    settings.sandbox_enabled = False
    assert run_tools_in_sandbox({"a.py": "print(1)"}) == []


def test_sandbox_skipped_when_docker_missing(monkeypatch):
    # Even with the flag on, a missing docker binary must not crash the pipeline.
    settings.sandbox_enabled = True
    monkeypatch.setattr("patchcourt.sandbox.runner.docker_available", lambda: False)
    assert run_tools_in_sandbox({"a.py": "print(1)"}) == []
    settings.sandbox_enabled = False


def test_sandbox_returns_empty_when_no_findings(monkeypatch):
    # Container runs but produces no findings.json → [] instead of raising.
    from types import SimpleNamespace

    settings.sandbox_enabled = True

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr("patchcourt.sandbox.runner.subprocess", SimpleNamespace(run=fake_run))
    assert run_tools_in_sandbox({"a.py": "print(1)"}) == []
    settings.sandbox_enabled = False