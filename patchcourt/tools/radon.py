"""Radon adapter — cyclomatic-complexity metrics."""
from __future__ import annotations

import asyncio
import json
import logging
import re

from patchcourt.tools.base import Finding, _binary_available, materialize

logger = logging.getLogger("patchcourt.tools.radon")

_COMPLEXITY_CAP = 10


class RadonAdapter:
    name = "radon"
    binary = "radon"

    def available(self) -> bool:
        return _binary_available(self.binary)

    async def run(self, file_contents: dict[str, str]) -> list[Finding]:
        if not self.available():
            logger.info("radon not installed — skipping")
            return []
        findings: list[Finding] = []
        with materialize(file_contents) as d:
            proc = await asyncio.create_subprocess_exec(
                "radon", "cc", "-j", d,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await proc.communicate()
        try:
            data = json.loads(out or b"{}")
        except json.JSONDecodeError:
            return []
        for path, blocks in data.items():
            for block in blocks:
                complexity = int(block.get("complexity", 0))
                if complexity >= _COMPLEXITY_CAP:
                    findings.append(
                        Finding(
                            tool="radon",
                            file=path.lstrip("/"),
                            line=int(block.get("lineno", 1)),
                            message=f"High cyclomatic complexity ({complexity}) in {block.get('name', '')}",
                            severity=3,
                            rule=f"COMPLEXITY>{_COMPLEXITY_CAP}",
                        )
                    )
        return findings


def _is_py(d):
    return any(re.search(r"\.py$", f) for f in d)