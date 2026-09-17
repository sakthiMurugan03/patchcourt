"""Security agent — vulnerability-focused review."""
from __future__ import annotations

from patchcourt.agents.base import BaseAgent


class SecurityAgent(BaseAgent):
    name = "security"

    def system_prompt(self) -> str:
        return (
            "You are a security-focused code reviewer. Find injection (SQL/command/SSRF), "
            "authz/authn flaws, secrets, unsafe deserialization, crypto misuse, path traversal. "
            "Respond ONLY as JSON: "
            '{"claims":[{"issue":"...","file":"...","line":1,"severity":1..5,'
            '"evidence":[{"tier":1..5,"text":"..."}],"confidence":0..1,"tier":1..5}]}\n'
            "Tier rules: T1 = external data path to sink (provable), T2 = direct API misuse, "
            "T3 = insecure pattern in diff, T4 = heuristic/cross-file suspicion, "
            "T5 = speculation without direct evidence."
        )

    def build_user_prompt(self, pr, rag_results, tool_findings=None):
        return (
            "Review this PR for SECURITY issues only.\n\n"
            + super().build_user_prompt(pr, rag_results, tool_findings)
        )