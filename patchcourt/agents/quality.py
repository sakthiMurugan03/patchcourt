"""Quality agent — correctness and code-quality review."""
from __future__ import annotations

from patchcourt.agents.base import BaseAgent


class QualityAgent(BaseAgent):
    name = "quality"

    def system_prompt(self) -> str:
        return (
            "You are a code-quality reviewer. Find bugs, race conditions, error-handling gaps, "
            "resource leaks, dead code, poor complexity, missing tests, non-idiomatic patterns. "
            "Respond ONLY as JSON: "
            '{"claims":[{"issue":"...","file":"...","line":1,"severity":1..5,'
            '"evidence":[{"tier":1..5,"text":"..."}],"confidence":0..1,"tier":1..5}]}\n'
            "Tier rules: T1 = provable bug from diff, T2 = clear API misuse, "
            "T3 = strong signal from diff context, T4 = inference across files, "
            "T5 = style preference / speculation."
        )

    def build_user_prompt(self, pr, rag_results, tool_findings=None):
        return (
            "Review this PR for QUALITY issues only.\n\n"
            + super().build_user_prompt(pr, rag_results, tool_findings)
        )