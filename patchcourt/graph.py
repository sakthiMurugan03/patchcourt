"""LangGraph orchestration: ingest → RAG → evidence → parallel agents → corroborate → conflict → debate → judge."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from patchcourt.agents import PragmatistAgent, QualityAgent, SecurityAgent
from patchcourt.agents.schemas import GraphState, PRContext
from patchcourt.debate import detect_conflicts, run_debate
from patchcourt.evidence import EvidenceEngine, corroborate_claims
from patchcourt.ingest import parse_pr_url, fetch_pr
from patchcourt.judge import build_report
from patchcourt.rag.store import clear, index_pr, query
from patchcourt.tools import run_enabled_tools

_INITIAL: dict[str, object] = {
    "pr": PRContext(),
    "rag_results": [],
    "tool_claims": [],
    "security_claims": [],
    "quality_claims": [],
    "pragmatist_claims": [],
    "all_claims": [],
    "conflicts": [],
    "debated_claims": [],
    "report": None,
}


def _evidence_runner():
    """Pick the tool runner: sandbox container when enabled, local tools otherwise."""
    from patchcourt.config import settings

    if settings.sandbox_enabled:
        from patchcourt.sandbox import run_tools_in_sandbox

        async def sandbox_runner(file_contents: dict[str, str]) -> list:
            return await asyncio.to_thread(run_tools_in_sandbox, file_contents)

        return sandbox_runner
    return run_enabled_tools


def build_graph() -> StateGraph:
    """Wire the PatchCourt review pipeline as a LangGraph state graph."""

    async def ingest(state: dict) -> dict[str, Any]:
        pr: PRContext = state["pr"]
        if pr.file_contents:
            return {"pr": pr}  # offline/demo mode — PR already provided
        fetched = await fetch_pr((pr.owner, pr.repo, pr.pr_number))
        return {"pr": fetched}

    async def rag_index(state: dict) -> dict[str, Any]:
        pr: PRContext = state["pr"]
        clear()
        index_pr(pr.file_contents)
        rag_results = query(pr.rag_query, n_results=8)
        return {"rag_results": rag_results}

    async def evidence(state: dict) -> dict[str, Any]:
        pr, rag = state["pr"], state["rag_results"]
        engine = EvidenceEngine(runner=_evidence_runner())
        tool_claims = await engine.analyze(pr.file_contents, rag)
        return {"tool_claims": tool_claims}

    async def security(state: dict) -> dict[str, Any]:
        pr, rag, tools = state["pr"], state["rag_results"], state["tool_claims"]
        return {"security_claims": await SecurityAgent().run(pr, rag, tools)}

    async def quality(state: dict) -> dict[str, Any]:
        pr, rag, tools = state["pr"], state["rag_results"], state["tool_claims"]
        return {"quality_claims": await QualityAgent().run(pr, rag, tools)}

    async def pragmatist(state: dict) -> dict[str, Any]:
        pr, rag, tools = state["pr"], state["rag_results"], state["tool_claims"]
        return {"pragmatist_claims": await PragmatistAgent().run(pr, rag, tools)}

    async def merge_all(state: dict) -> dict[str, Any]:
        llm = state["security_claims"] + state["quality_claims"] + state["pragmatist_claims"]
        all_claims = corroborate_claims(state.get("tool_claims", []), llm)
        return {"all_claims": all_claims}

    async def detect(state: dict) -> dict[str, Any]:
        conflicts = detect_conflicts(state["all_claims"])
        return {"conflicts": conflicts}

    def has_conflicts(state: dict) -> str:
        return "debate" if state.get("conflicts") else "judge"

    async def debate(state: dict) -> dict[str, Any]:
        debated = await run_debate(state.get("conflicts", []), state.get("pr", PRContext()))
        return {"debated_claims": debated}

    async def judge(state: dict) -> dict[str, Any]:
        pr: PRContext = state.get("pr", PRContext())
        url = f"https://github.com/{pr.owner}/{pr.repo}/pull/{pr.pr_number}"
        report = build_report(url, state.get("all_claims", []), state.get("debated_claims", []))
        return {"report": report}

    g = StateGraph(GraphState)
    g.add_node("ingest", ingest)
    g.add_node("rag", rag_index)
    g.add_node("evidence", evidence)
    g.add_node("security", security)
    g.add_node("quality", quality)
    g.add_node("pragmatist", pragmatist)
    g.add_node("merge_all", merge_all)
    g.add_node("detect", detect)
    g.add_node("debate", debate)
    g.add_node("judge", judge)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "rag")
    g.add_edge("rag", "evidence")
    g.add_edge("evidence", "security")
    g.add_edge("evidence", "quality")
    g.add_edge("evidence", "pragmatist")
    g.add_edge("security", "merge_all")
    g.add_edge("quality", "merge_all")
    g.add_edge("pragmatist", "merge_all")
    g.add_edge("merge_all", "detect")
    g.add_conditional_edges(
        "detect",
        has_conflicts,
        {"debate": "debate", "judge": "judge"},
    )
    g.add_edge("debate", "judge")
    g.add_edge("judge", END)
    g = g.compile()
    return g


def _initial_state(pr: PRContext | None = None) -> dict:
    base = dict(_INITIAL)
    if pr is not None:
        base["pr"] = pr
    return base


def _final_report(state: dict) -> Any:
    report = state.get("report")
    if report is None:
        raise RuntimeError("review graph did not produce a report")
    return report


async def run_review(pr_url: str, pr: PRContext | None = None) -> Any:
    """Run a full review. If ``pr`` is given, the fetch step is skipped
    (used for offline/demo runs). Returns the final ReviewReport."""
    if pr is None:
        owner, repo, num = parse_pr_url(pr_url)
        pr = PRContext(owner=owner, repo=repo, pr_number=num)
    graph = build_graph()
    state: dict = _initial_state(pr)
    final_state: dict = state
    async for step in graph.astream(state, stream_mode="values"):
        final_state = dict(step) if isinstance(step, dict) else step
    report = _final_report(final_state)
    _persist_audit(report)
    return report


def _persist_audit(report) -> None:
    from patchcourt.config import settings

    if not settings.database_url:
        return
    try:
        from patchcourt.db import store_audit

        store_audit(report)
    except Exception:
        logging.getLogger("patchcourt.graph").exception("could not persist audit record")