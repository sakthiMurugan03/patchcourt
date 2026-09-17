"""Sandbox — run the PR's untrusted code + analysis tools inside an isolated container."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections import defaultdict

from patchcourt.tools import Finding

logger = logging.getLogger("patchcourt.sandbox")


def docker_available() -> bool:
    return shutil.which("docker") is not None


def run_tools_in_sandbox(file_contents: dict[str, str]) -> list[Finding]:
    """Materialize files, run them through the sandbox image, parse findings.json."""
    from patchcourt.config import settings

    if not settings.sandbox_enabled:
        logger.info("sandbox disabled (SANDBOX_ENABLED=false) — skipping container run")
        return []
    if not docker_available():
        logger.warning("docker binary not found — sandbox skipped")
        return []

    import os
    import tempfile

    base_dir = (settings.sandbox_workdir or "").strip() or None
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=base_dir, prefix="patchcourt_sbx_")
    try:
        for fname, content in file_contents.items():
            path = os.path.join(workdir, fname.lstrip("/"))
            os.makedirs(os.path.dirname(path) or workdir, exist_ok=True)
            with open(path, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(content)

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{workdir}:{settings.sandbox_workspace}:rw",
            "--network", "none",
            "--memory", "512m",
            "--pids-limit", "256",
            settings.sandbox_image,
        ]
        logger.info("running sandbox: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, timeout=600)
        if proc.returncode != 0:
            logger.warning("sandbox exited %d: %s", proc.returncode, proc.stderr.decode(errors="replace")[:500])

        with open(os.path.join(workdir, "findings.json")) as fh:
            raw = json.load(fh)
        return [_finding_from_dict(d) for d in raw]
    except FileNotFoundError:
        logger.warning("no findings.json produced by sandbox")
        return []
    except Exception as exc:  # noqa: BLE001
        logger.exception("sandbox run failed: %s", exc)
        return []
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _finding_from_dict(d: dict) -> Finding:
    file = str(d.get("file", "unknown"))
    file = file.removeprefix("/workspace/").lstrip("/")
    return Finding(
        tool=str(d.get("tool", "sandbox")),
        file=file,
        line=int(d.get("line", 0) or 0),
        message=str(d.get("message", ""))[:500],
        severity=int(d.get("severity", 3)),
        rule=str(d.get("rule", "")),
    )


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    """Deduplicate identical (tool, file, line) findings."""
    seen: set[tuple] = set()
    out: list[Finding] = []
    for f in findings:
        key = (f.tool, f.file, f.line)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out