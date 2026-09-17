"""Evidence Engine + tier assignment + corroboration rules."""
import pytest

from patchcourt.agents.schemas import Claim, Evidence
from patchcourt.evidence import (
    EvidenceEngine,
    corroborate_claims,
    normalize_findings,
    tier_for_findings,
)
from patchcourt.judge import build_report
from patchcourt.tools import Finding
from patchcourt.tools.synthetic import SyntheticAdapter


def f(tool, file="a.py", line=5, sev=5, msg="boom", rule="R"):
    return Finding(tool=tool, file=file, line=line, message=msg, severity=sev, rule=rule)


def llm_claim(severity=5, file="a.py", line=5, tier=5, conf=1.0):
    return Claim(
        agent="security", issue="LLM guessed a bug", file=file, line=line,
        severity=severity, evidence=[Evidence(tier=tier, text="assertion")],
        confidence=conf, tier=tier,
    )


# ── tier assignment ──────────────────────────────────────────────────
def test_single_tool_flag_is_t1():
    tier, corr = tier_for_findings([f("semgrep")])
    assert tier == 1 and not corr


def test_two_tools_agreeing_is_t2_corroborated():
    tier, corr = tier_for_findings([f("semgrep"), f("bandit")])
    assert tier == 2 and corr


def test_same_tool_twice_is_not_corroboration():
    tier, corr = tier_for_findings([f("semgrep"), f("semgrep")])
    assert tier == 1 and not corr


def test_normalize_groups_by_file_line_and_uses_max_severity():
    claims = normalize_findings(
        [f("semgrep", line=5, sev=3), f("bandit", line=5, sev=2), f("semgrep", line=9, sev=5)]
    )
    by_line = {c.line: c for c in claims}
    assert set(by_line) == {5, 9}
    assert by_line[5].severity == 3
    assert by_line[5].tier == 2 and by_line[5].corroborated     # two tools, same line
    assert by_line[9].tier == 1 and not by_line[9].corroborated  # one tool


# ── corroboration ────────────────────────────────────────────────────
def test_llm_claim_matching_tool_finding_is_upgraded():
    tool = normalize_findings([f("semgrep", line=5)])
    llm = [llm_claim(tier=5)]  # pure LLM assertion on the SAME file/line
    merged = corroborate_claims(tool, llm)
    upgraded = [c for c in merged if c.source == "llm"]
    assert upgraded[0].corroborated is True
    assert upgraded[0].tier == 1  # upgraded from T5 to tool tier


def test_llm_claim_on_other_line_stays_unbacked():
    tool = normalize_findings([f("semgrep", line=5)])
    llm = [llm_claim(tier=5, line=99)]
    merged = corroborate_claims(tool, llm)
    kept = [c for c in merged if c.source == "llm"]
    assert kept[0].corroborated is False
    assert kept[0].tier == 5


# ── BLOCK hard rule + corroboration interplay ────────────────────────
def test_uncorroborated_llm_only_claim_cannot_produce_block():
    """A bare LLM assertion (T5, corroborated=False) can never trigger BLOCK."""
    claims = [llm_claim(severity=5, tier=5, conf=1.0) for _ in range(25)]
    report = build_report("https://github.com/a/b/pull/1", claims, [])
    assert report.overall_score >= 10.0
    assert report.verdict != "BLOCK"


def test_tool_corroborated_claim_pushes_block():
    tool = normalize_findings([f("semgrep", line=5, sev=5)])
    llm = [llm_claim(tier=5)]
    merged = corroborate_claims(tool, llm)
    report = build_report("https://github.com/a/b/pull/1", merged, [])
    assert report.verdict == "BLOCK"  # tool-backed evidence crosses the threshold


# ── synthetic scanner + full engine ──────────────────────────────────
@pytest.mark.asyncio
async def test_evidence_engine_uses_synthetic_scanner():
    engine = EvidenceEngine(runner=lambda fc: SyntheticAdapter().run(fc))
    claims = await engine.analyze(
        {"app.py": '+subprocess.call(cmd, shell=True)\n+x = "SELECT * FROM t WHERE id = " + uid\n'}
    )
    assert len(claims) >= 2
    assert all(c.source == "tool" for c in claims)
    assert all(c.corroborated is False for c in claims)  # only one tool
    assert all(c.tier == 1 for c in claims)