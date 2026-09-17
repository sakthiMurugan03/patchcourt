"""Shared data models for PatchCourt."""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    tier: int = Field(ge=1, le=5, description="Evidence tier T1–T5")
    text: str


class Claim(BaseModel):
    agent: str = ""
    issue: str
    file: str
    line: int = 0
    severity: int = Field(ge=1, le=5)
    evidence: list[Evidence]
    confidence: float = Field(ge=0.0, le=1.0)
    tier: int = Field(default=3, ge=1, le=5, description="Dominant tier for this claim")
    corroborated: bool = Field(default=False, description="Backed by a static-analysis tool finding")
    source: str = Field(default="llm", description="'tool' or 'llm'")


class DebatedClaim(BaseModel):
    claim: Claim
    supporting: str = ""
    opposing: str = ""
    rounds: int = 0


class FileReport(BaseModel):
    file: str
    claims: list[Claim]
    score: float = 0.0


class ReviewReport(BaseModel):
    pr_url: str
    overall_score: float = 0.0
    verdict: str = "MERGE"
    files: list[FileReport] = []
    claims: list[Claim] = []
    debate_transcripts: list[dict] = []


class PRContext(BaseModel):
    owner: str = ""
    repo: str = ""
    pr_number: int = 0
    title: str = ""
    body: str = ""
    diff: str = ""
    changed_files: list[Any] = []
    file_contents: dict[str, str] = {}
    patches: dict[str, str] = {}
    rag_query: str = ""


class GraphState(TypedDict, total=False):
    """LangGraph channel state (TypedDict → one reducible channel per field)."""

    pr: PRContext
    rag_results: list[dict]
    tool_claims: list[Claim]
    security_claims: list[Claim]
    quality_claims: list[Claim]
    pragmatist_claims: list[Claim]
    all_claims: list[Claim]
    conflicts: list[dict]
    debated_claims: list[DebatedClaim]
    report: ReviewReport