"""Synthetic adapter — deterministic rule-based scanner (offline demo mode).

No external binary required. Scans added lines (``+``) of each changed file
against a small set of high-signal security patterns so the full Evidence-tier
pipeline can be demonstrated without installing SAST tools.
"""
from __future__ import annotations

import logging
import re

from patchcourt.tools.base import Finding

logger = logging.getLogger("patchcourt.tools.synthetic")

_PATTERNS: list[tuple[re.Pattern, int, str, str]] = [
    (re.compile(r"subprocess\.(call|Popen|run)\([^)]*shell\s*=\s*True"), 5, "SHELL_TRUE", "subprocess with shell=True — command injection risk"),
    (re.compile(r"os\.system\("), 5, "OS_SYSTEM", "os.system() executes a shell — injection risk"),
    (re.compile(r"\b(exec|eval)\("), 5, "DYN_EXEC", "dynamic code execution via exec/eval"),
    (re.compile(r"['\"]\s*SELECT[^'\"]*['\"]?\s*\+\s*|[fF]?['\"]\s*SELECT"), 5, "SQL_CONCAT", "SQL string concatenation — injection risk"),
    (re.compile(r"(?i)\b\w*(password|passwd|secret|token|api[_-]?key)\w*\s*=\s*['\"][^'\"]{6,}['\"]"), 4, "HARDCODED_SECRET", "hardcoded secret value"),
    (re.compile(r"requests\.(get|post|put|delete)\(['\"]http://"), 3, "HTTP_PLAINTEXT", "plaintext HTTP request"),
    (re.compile(r"pickle\.loads?\(|yaml\.load\([^)]*Loader\s*=[^)]*FullLoader"), 4, "UNSAFE_DESERIAL", "unsafe deserialization"),
]


class SyntheticAdapter:
    name = "synthetic"
    binary = None

    def available(self) -> bool:
        return True  # gating handled by config

    @staticmethod
    def _is_patch(text: str) -> bool:
        stripped = text.lstrip()
        return any(l.startswith(("+", "-")) for l in stripped.splitlines()[:50] if l.strip())

    async def run(self, file_contents: dict[str, str]) -> list[Finding]:
        findings: list[Finding] = []
        for fname, content in file_contents.items():
            patch_style = self._is_patch(content)
            for lineno, raw in enumerate(content.splitlines(), start=1):
                if patch_style:
                    if not raw.lstrip().startswith("+"):
                        continue  # only added lines in patch text
                    line = raw.lstrip()[1:].strip()
                else:
                    line = raw.strip()
                for pat, sev, rule, msg in _PATTERNS:
                    if pat.search(line):
                        findings.append(
                            Finding(tool="synthetic", file=fname, line=lineno, message=msg, severity=sev, rule=rule)
                        )
        if findings:
            logger.info("synthetic scanner: %d finding(s)", len(findings))
        return findings