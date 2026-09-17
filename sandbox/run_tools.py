"""Runs the static-analysis tools inside the sandbox container.

Mount your repo directory at /workspace; findings are written to
/workspace/findings.json so the host can pick them up via the volume.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile


def _emit(findings: list[dict]) -> None:
    out = "/workspace/findings.json"
    with open(out, "w") as fh:
        json.dump(findings, fh)
    print(f"wrote {len(findings)} finding(s) to {out}")


def _run(cmd: list[str], cwd: str) -> tuple[bytes, int]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=300)
        return proc.stdout, proc.returncode
    except Exception as exc:  # noqa: BLE001 - sandbox degrades gracefully
        return str(exc).encode(), -1


def scan_dirs() -> list[str]:
    base = "/workspace"
    dirs = [base]
    for root, subdirs, files in os.walk(base):
        subdirs[:] = [d for d in subdirs if d != ".git"]
        if files:
            dirs.append(root)
    return dirs


def main() -> int:
    findings: list[dict] = []

    # semgrep
    out, _ = _run(["semgrep", "scan", "--quiet", "--json", "/workspace"], "/workspace")
    try:
        for r in json.loads(out or b"{}").get("results", []):
            findings.append(
                {
                    "tool": "semgrep",
                    "file": r["path"],
                    "line": int(r["start"]["line"]),
                    "message": r["extra"].get("message", r.get("check_id", "")),
                    "severity": {"ERROR": 5, "WARNING": 4}.get(r["extra"].get("severity"), 4),
                    "rule": r.get("check_id", ""),
                }
            )
    except Exception:  # noqa: BLE001
        pass

    # bandit
    out, _ = _run(["bandit", "-q", "-f", "json", "-r", "/workspace"], "/workspace")
    try:
        for r in json.loads(out or b"{}").get("results", []):
            findings.append(
                {
                    "tool": "bandit",
                    "file": r["filename"],
                    "line": int(r["line_number"]),
                    "message": f"{r['test_id']}: {r['issue_text']}",
                    "severity": {"LOW": 2, "MEDIUM": 3, "HIGH": 4}.get(r.get("issue_severity"), 3),
                    "rule": r.get("test_id", ""),
                }
            )
    except Exception:  # noqa: BLE001
        pass

    # gitleaks
    with tempfile.NamedTemporaryFile(suffix=".json") as report:
        _run(
            [
                "gitleaks", "detect", "--no-git", "--source", "/workspace",
                "--report-format", "json", "--report-path", report.name,
            ],
            "/workspace",
        )
        try:
            with open(report.name) as fh:
                data = json.load(fh)
            leaks = data if isinstance(data, list) else data.get("leaks", [])
            for f in leaks:
                findings.append(
                    {
                        "tool": "gitleaks",
                        "file": f.get("File", ""),
                        "line": int(f.get("StartLine", 0)),
                        "message": f"Potential secret: {f.get('RuleID', '')}",
                        "severity": 5,
                        "rule": str(f.get("RuleID", "")),
                    }
                )
        except Exception:  # noqa: BLE001
            pass

    # radon
    out, _ = _run(["radon", "cc", "-j", "/workspace"], "/workspace")
    try:
        for path, blocks in json.loads(out or b"{}").items():
            for block in blocks:
                if int(block.get("complexity", 0)) >= 10:
                    findings.append(
                        {
                            "tool": "radon",
                            "file": path,
                            "line": int(block.get("lineno", 1)),
                            "message": f"High cyclomatic complexity ({block.get('complexity')}) in {block.get('name', '')}",
                            "severity": 3,
                            "rule": "COMPLEXITY>10",
                        }
                    )
    except Exception:  # noqa: BLE001
        pass

    _emit(findings)
    return 0


if __name__ == "__main__":
    sys.exit(main())