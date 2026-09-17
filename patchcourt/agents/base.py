"""Base agent with claim parsing."""
from __future__ import annotations

from patchcourt.agents.schemas import Claim, Evidence, PRContext
from patchcourt.llm import LLMClient


def render_tool_findings(findings: list[Claim]) -> str:
    """Render evidence-engine claims for an agent prompt."""
    if not findings:
        return ""
    lines = [f"[{c.agent}] {c.file}:{c.line} sev{c.severity} T{c.tier} — {c.issue}" for c in findings[:25]]
    return "\n".join(lines)


class BaseAgent:
    name = "base"

    def __init__(self, llm: LLMClient | None = None) -> None:
        from patchcourt.llm import get_llm

        self.llm = llm or get_llm()

    def system_prompt(self) -> str:
        return (
            "You are a code reviewer. You are given static-analysis tool findings and a PR diff. "
            "Corroborate or dispute each tool finding on file+line. You may also raise issues no "
            "tool caught — but those are UNBACKED (peer-review only). Respond ONLY as JSON: "
            '{"claims":[{"issue":"...","file":"...","line":1,"severity":1..5,'
            '"evidence":[{"tier":1..5,"text":"..."}],"confidence":0..1,"tier":1..5}]}\n'
            "Tier rules: T1 = a tool flags this file/line, T2 = two tools agree, "
            "T3 = repo policy/RAG, T4 = git precedent, T5 = pure LLM assertion."
        )

    def build_user_prompt(self, pr: PRContext, rag_results: list[dict], tool_findings: list | None = None) -> str:
        chunks = "\n\n".join(
            f"[chunk from {r['metadata'].get('file', '?')}]\n{r['document'][:2000]}"
            for r in rag_results[:6]
        )
        tools = render_tool_findings(tool_findings or [])
        section = f"\n\nSTATIC-ANALYSIS FINDINGS:\n{tools}\n" if tools else ""
        return (
            f"PR: {pr.title}\n\n{pr.diff[:6000]}{section}"
            f"\n\nGROUNDING:\n{chunks[:4000]}"
        )

    def parse(self, payload: dict) -> list[Claim]:
        claims: list[Claim] = []
        for raw in payload.get("claims", []):
            evis = [
                Evidence(tier=min(5, max(1, int(e.get("tier", 3)))), text=str(e.get("text", ""))[:500])
                for e in raw.get("evidence", [])
            ]
            if not evis:
                evis = [Evidence(tier=3, text="no evidence provided")]
            dominant_tier = min(e.tier for e in evis)
            claims.append(
                Claim(
                    agent=self.name,
                    issue=str(raw.get("issue", ""))[:500],
                    file=str(raw.get("file", "unknown")),
                    line=int(raw.get("line", 0)),
                    severity=min(5, max(1, int(raw.get("severity", 3)))),
                    confidence=min(1.0, max(0.0, float(raw.get("confidence", 0.5)))),
                    evidence=evis,
                    tier=min(5, max(1, int(raw.get("tier", dominant_tier)))),
                )
            )
        return claims

    async def run(
        self,
        pr: PRContext,
        rag_results: list[dict],
        tool_findings: list | None = None,
    ) -> list[Claim]:
        payload = await self.llm.generate(
            self.system_prompt(), self.build_user_prompt(pr, rag_results, tool_findings)
        )
        return self.parse(payload)