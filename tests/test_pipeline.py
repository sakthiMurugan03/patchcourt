"""End-to-end graph run offline: fake LLM, real RAG + LangGraph + judge."""
import asyncio

import pytest

from patchcourt.agents.schemas import PRContext
from patchcourt.graph import run_review
from patchcourt.runtime_llm_config import reset_runtime_config
from patchcourt.llm import reset_llm


class FakeLLM:
    def __init__(self, claims_by_agent: dict[str, list[dict]]):
        self._by = claims_by_agent

    async def generate(self, system: str, user: str) -> dict:
        lowered = system.lower()
        if "sec" in lowered and "security" in lowered:
            agent = "security"
        elif "quality" in lowered:
            agent = "quality"
        elif "pragm" in lowered:
            agent = "pragmatist"
        else:
            agent = "fallback"
        return {"claims": self._by.get(agent, [])}


def claim(issue, file, severity, tier, agent, conf=1.0, line=1):
    return {
        "issue": issue, "file": file, "line": line, "severity": severity,
        "evidence": [{"tier": tier, "text": "evidence"}], "confidence": conf, "tier": tier,
    }


def fake_llm(claims_by_agent):
    from patchcourt.agents.base import BaseAgent
    from patchcourt.rag.store import _client as rag_client

    BaseAgent._original_run = getattr(BaseAgent, "_original_run", None)
    _patch = claims_by_agent

    async def run(self, pr, rag_results, tool_findings=None):
        return self.parse(await FakeLLM(_patch).generate(self.system_prompt(), ""))

    _orig = BaseAgent.run
    BaseAgent.run = run

    def clear_llm():
        BaseAgent.run = _orig

    return clear_llm


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    from patchcourt.rag import store as rag_store

    monkeypatch.setattr(rag_store, "_client", None)
    monkeypatch.setattr(rag_store, "_EMBEDDER", None)
    monkeypatch.setattr(rag_store, "_sentence_transformers", None)
    
    # Reset runtime config and LLM client to use mock mode
    reset_runtime_config()
    reset_llm()
    yield


def _pr(diff="+def login(): pass"):
    return PRContext(
        owner="demo", repo="demo", pr_number=1, title="Demo PR",
        body="try it out", diff=diff, file_contents={"app.py": diff},
        rag_query="demo pr",
    )


async def test_full_pipeline_merge_verdict():
    patch = fake_llm({
        "security": [claim("unused import import os", "app.py", 1, 5, "security", 0.2)],
        "quality": [claim("unused import import os", "app.py", 1, 5, "quality", 0.2)],
        "pragmatist": [],
    })
    try:
        report = await run_review("https://github.com/demo/demo/pull/1", pr=_pr())
        assert report.verdict == "MERGE"
        assert report.overall_score < 4.0
    finally:
        patch()


async def test_full_pipeline_block_with_t1_evidence():
    patch = fake_llm({
        "security": [claim("sql injection in login", "app.py", 5, 1, "security")],
        "quality": [claim("sql injection in login", "app.py", 5, 1, "quality")],
        "pragmatist": [claim("sql injection in login", "app.py", 5, 1, "pragmatist")],
    })
    try:
        report = await run_review("https://github.com/demo/demo/pull/1", pr=_pr())
        assert report.verdict == "BLOCK"
        assert len(report.claims) == 3
    finally:
        patch()


async def test_full_pipeline_t5_cannot_block():
    patch = fake_llm({
        "security": [claim("maybe could be bad", "app.py", 5, 5, "security")],
        "quality": [claim("maybe could be bad", "app.py", 5, 5, "quality")],
        "pragmatist": [claim("maybe could be bad", "app.py", 5, 5, "pragmatist")],
    })
    try:
        report = await run_review("https://github.com/demo/demo/pull/1", pr=_pr())
        assert report.verdict != "BLOCK"
    finally:
        patch()


async def test_debate_path_with_conflict():
    patch = fake_llm({
        "security": [claim("sql injection", "app.py", 5, 1, "security")],
        "pragmatist": [claim("sql injection", "app.py", 1, 1, "pragmatist")],
        "quality": [],
    })
    try:
        report = await run_review("https://github.com/demo/demo/pull/1", pr=_pr())
        assert report.debate_transcripts, "expected a gated debate"
        debate = report.debate_transcripts[0]
        assert debate["rounds"] >= 1
        assert debate["rounds"] <= 2  # bounded
    finally:
        patch()