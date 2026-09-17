"""Judge scoring + the BLOCK-on-T5-alone hard constraint."""
import pytest

from patchcourt.agents.schemas import Claim, Evidence
from patchcourt.judge.scoring import (
    claim_score,
    is_t5_only,
    build_report,
    verdict_for,
)


def mk(issue, severity=3, tier=3, evid_tiers=None, conf=1.0, file="a.py", agent="quality"):
    tiers = evid_tiers or [tier]
    return Claim(
        agent=agent, issue=issue, file=file, line=1, severity=severity,
        evidence=[Evidence(tier=t, text="e") for t in tiers],
        confidence=conf, tier=tier,
    )


def test_claim_score_math():
    # severity 5 * T1 weight 1.0 * corroboration 1.0 * confidence 1.0 = 5.0
    c = mk("SQL injection", severity=5, tier=1, evid_tiers=[1], conf=1.0)
    assert claim_score(c) == pytest.approx(5.0)
    # half confidence halves the score
    c2 = mk("SQL injection", severity=5, tier=1, evid_tiers=[1], conf=0.5)
    assert claim_score(c2) == pytest.approx(2.5)
    # T5 evidence-clamped claim weights far less
    c3 = mk("vibe issue", severity=5, tier=5, evid_tiers=[5], conf=1.0)
    assert claim_score(c3) == pytest.approx(5.0 * 0.1)


def test_corroboration_multiplier():
    solo = claim_score(mk("bug", severity=2, tier=2, evid_tiers=[2], conf=1.0))
    corroborated = claim_score(
        mk("bug", severity=2, tier=2, evid_tiers=[2], conf=1.0),
        corroboration=1.25,
    )
    assert corroborated > solo
    assert corroborated == pytest.approx(2.0 * 0.8 * 1.25)


def test_verdict_thresholds():
    assert verdict_for(2.0) == "MERGE"
    assert verdict_for(5.0) == "NEEDS_REVIEW"
    assert verdict_for(12.0) == "BLOCK"


def test_is_t5_only():
    assert is_t5_only(mk("x", evid_tiers=[5]))
    assert is_t5_only(mk("x", evid_tiers=[5, 5]))
    assert not is_t5_only(mk("x", evid_tiers=[5, 4]))
    assert not is_t5_only(mk("x", evid_tiers=[3]))


def test_block_never_rests_on_t5_alone():
    """Even 25 corroborated T5 claims (score ≥ 10) must NOT produce BLOCK."""
    t5s = [mk("speculation", severity=5, tier=5, evid_tiers=[5], conf=1.0) for _ in range(25)]
    report = build_report("https://github.com/a/b/pull/1", t5s, [])
    assert report.overall_score >= 10.0
    assert report.verdict != "BLOCK"
    assert report.verdict == "NEEDS_REVIEW"  # downgraded from a would-be BLOCK


def test_executive_rule_via_report():
    """Full pipeline rule: a report whose only claim is T5 can never be BLOCK."""
    only_t5 = mk("speculation", severity=5, tier=5, evid_tiers=[5], conf=1.0)
    report = build_report("https://github.com/a/b/pull/1", [only_t5], [])
    assert report.verdict != "BLOCK"
    assert report.verdict in ("MERGE", "NEEDS_REVIEW")


def test_block_allowed_with_real_evidence():
    real1 = mk("RCE in auth", severity=5, tier=1, evid_tiers=[1], conf=1.0, agent="security")
    real2 = mk("RCE in auth", severity=5, tier=1, evid_tiers=[1], conf=1.0, agent="quality")
    t5 = mk("speculation", severity=5, tier=5, evid_tiers=[5], conf=1.0)
    report = build_report("https://github.com/a/b/pull/1", [real1, real2, t5], [])
    assert report.overall_score >= 10.0
    assert report.verdict == "BLOCK"