"""Semgrep adapter — SAST rules over the changed files."""
from __future__ import annotations

import asyncio
import json
import logging
import os

from patchcourt.tools.base import Finding, _binary_available, materialize

logger = logging.getLogger("patchcourt.tools.semgrep")


class SemgrepAdapter:
    name = "semgrep"
    binary = "semgrep"

    def available(self) -> bool:
        return _binary_available(self.binary)

    async def run(self, file_contents: dict[str, str]) -> list[Finding]:
        if not self.available():
            logger.info("semgrep not installed — skipping")
            return []
        findings: list[Finding] = []
        with materialize(file_contents) as d:
            proc = await asyncio.create_subprocess_exec(
                "semgrep", "scan", "--quiet", "--json", d,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await proc.communicate()
        try:
            data = json.loads(out or b"{}")
        except json.JSONDecodeError:
            return []
        sev_map = {"ERROR": 5, "WARNING": 4, "INFO": 2}
        for r in data.get("results", []):
            path = r.get("path", "")
            if not path.startswith(d):
                continue
            rel = os.path.relpath(path, d)
            extra = r.get("extra", {})
            findings.append(
                Finding(
                    tool="semgrep",
                    file=rel,
                    line=int(r.get("start", {}).get("line", 0)),
                    message=f"{extra.get('message', r.get('check_id', ''))}",
                    severity=sev_map.get(str(extra.get("severity")), 4),
                    rule=r.get("check_id", ""),
                )
            )
        return findings