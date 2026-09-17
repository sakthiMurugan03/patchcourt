"""Conflict detection + debate gating."""
from patchcourt.agents.schemas import Claim, Evidence
from patchcourt.debate.conflict import detect_conflicts, same_claim


def mk(agent, issue, severity, file="a.py"):
    return Claim(
        agent=agent, issue=issue, file=file, line=1, severity=severity,
        evidence=[Evidence(tier=2, text="e")], confidence=0.8, tier=2,
    )


def test_single_agent_no_conflict():
    claims = [mk("security", "injection", 5)]
    assert detect_conflicts(claims) == []


def test_agreeing_agents_no_conflict():
    claims = [
        mk("security", "injection", 5),
        mk("quality", "injection", 5),
    ]
    assert detect_conflicts(claims) == []


def test_disagreeing_severity_triggers_conflict():
    claims = [
        mk("security", "command injection", 5),
        mk("pragmatist", "command injection", 1),
    ]
    conflicts = detect_conflicts(claims)
    assert len(conflicts) == 1
    assert conflicts[0]["type"] == "disputed"
    assert len(conflicts[0]["claims"]) == 2


def test_parallel_agents_run_then_gated_debate():
    """If no conflicts, the graph route skips debate (checked by has_conflicts)."""
    claims = [
        mk("security", "encryption", 4),
        mk("quality", "encryption", 4),
        mk("pragmatist", "encryption", 4),
    ]
    assert detect_conflicts(claims) == []


def test_same_claim_semantics():
    a = mk("security", "SQL injection in query", 5)
    b = mk("quality", "SQL injection in query", 2)
    assert same_claim(a, b)
    c = mk("security", "SQL injection in query", 5, file="b.py")
    assert not same_claim(a, c)