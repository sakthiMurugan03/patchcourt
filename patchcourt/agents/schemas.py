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
    code_snippet: str = Field(default="", description="Target file snippet shown to the agents")
    verdict_summary: str = Field(default="", description="Plain-English developer takeaway")


class FileReport(BaseModel):
    file: str
    claims: list[Claim]
    score: float = 0.0


class PolicyRef(BaseModel):
    id: str
    title: str
    excerpt: str = ""
    source: str = ""


class CorrelationGroup(BaseModel):
    file: str
    line: int = 0
    tools: list[str] = []
    findings: list[dict] = []
    relationship: str = "solo"
    severity_range: list[int] = []
    disputed: bool = False


class FindingAssessment(BaseModel):
    tool: str = ""
    file: str = ""
    line: int = 0
    rule: str = ""
    message: str = ""
    severity: int = Field(default=3, ge=1, le=5)
    category: str = "unknown"
    status: str = "UNCERTAIN"
    rationale: str = ""
    corroborated: bool = False
    corroborating_tools: list[str] = []
    policies: list[PolicyRef] = []
    contextual_priority: str = ""
    contextual_action: str = ""
    evidence: list[Evidence] = []


class ReviewReport(BaseModel):
    pr_url: str
    overall_score: float = 0.0
    verdict: str = "MERGE"
    files: list[FileReport] = []
    claims: list[Claim] = []
    debate_transcripts: list[dict] = []
    finding_assessments: list[FindingAssessment] = []
    correlations: list[CorrelationGroup] = []
    contextual_summary: dict = {}
    baseline_report: dict | None = None


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
    raw_findings: list
    tool_claims: list[Claim]
    correlations: list[CorrelationGroup]
    finding_assessments: list[FindingAssessment]
    security_claims: list[Claim]
    quality_claims: list[Claim]
    pragmatist_claims: list[Claim]
    all_claims: list[Claim]
    conflicts: list[dict]
    debated_claims: list[DebatedClaim]
    report: ReviewReport