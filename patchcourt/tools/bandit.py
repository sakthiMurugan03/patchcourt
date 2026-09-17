"""Bandit adapter — Python security linter."""
from __future__ import annotations

import asyncio
import json
import logging
import os

from patchcourt.tools.base import Finding, _binary_available, materialize

logger = logging.getLogger("patchcourt.tools.bandit")


class BanditAdapter:
    name = "bandit"
    binary = "bandit"

    def available(self) -> bool:
        return _binary_available(self.binary)

    async def run(self, file_contents: dict[str, str]) -> list[Finding]:
        if not self.available():
            logger.info("bandit not installed — skipping")
            return []
        findings: list[Finding] = []
        with materialize(file_contents) as d:
            proc = await asyncio.create_subprocess_exec(
                "bandit", "-q", "-f", "json", "-r", d,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await proc.communicate()
        try:
            data = json.loads(out or b"{}")
        except json.JSONDecodeError:
            return []
        sev_map = {"LOW": 2, "MEDIUM": 3, "HIGH": 4}
        for r in data.get("results", []):
            filename = r.get("filename", "")
            if not filename.startswith(d):
                continue
            findings.append(
                Finding(
                    tool="bandit",
                    file=os.path.relpath(filename, d),
                    line=int(r.get("line_number", 0)),
                    message=f"{r.get('test_id', '')}: {r.get('issue_text', '')}",
                    severity=sev_map.get(str(r.get("issue_severity", "MEDIUM")), 3),
                    rule=r.get("test_id", ""),
                )
            )
        return findings