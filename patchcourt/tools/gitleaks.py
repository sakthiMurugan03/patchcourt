"""Gitleaks adapter — secret scanning."""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile

from patchcourt.tools.base import Finding, _binary_available, materialize

logger = logging.getLogger("patchcourt.tools.gitleaks")


class GitleaksAdapter:
    name = "gitleaks"
    binary = "gitleaks"

    def available(self) -> bool:
        return _binary_available(self.binary)

    async def run(self, file_contents: dict[str, str]) -> list[Finding]:
        if not self.available():
            logger.info("gitleaks not installed — skipping")
            return []
        findings: list[Finding] = []
        with materialize(file_contents) as d, tempfile.NamedTemporaryFile(suffix=".json") as report:
            proc = await asyncio.create_subprocess_exec(
                "gitleaks", "detect", "--no-git", "--source", d,
                "--report-format", "json", "--report-path", report.name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            try:
                report.seek(0)
                data = json.loads(report.read())
            except json.JSONDecodeError:
                return []
        leaks = data if isinstance(data, list) else data.get("leaks", [])
        for f in leaks:
            path = f.get("File", f.get("file", ""))
            start = f.get("StartLine", f.get("start_line", 0))
            findings.append(
                Finding(
                    tool="gitleaks",
                    file=path.lstrip("/"),
                    line=int(start),
                    message=f"Potential secret: {f.get('RuleID', f.get('rule', ''))}",
                    severity=5,
                    rule=str(f.get("RuleID", f.get("rule", ""))),
                )
            )
        return findings