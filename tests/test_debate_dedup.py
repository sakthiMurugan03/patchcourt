"""Anti-redundancy controls for the Courtroom Debate.

Covers the three guarantees added to the debate logic:
  1. similarity/dedup detection of repeated arguments,
  2. prompt tuning that tells both sides not to repeat themselves,
  3. clean convergence/termination instead of looping on redundant turns.
"""
import pytest

from patchcourt.agents.schemas import Claim, Evidence
from patchcourt.debate import debate as debate_mod
from patchcourt.debate.debate import (
    _NO_REPEAT_RULE,
    _build_defense_prompt,
    _build_prosecution_prompt,
    _is_redundant,
    _similarity,
    run_debate,
)


def mk(agent, issue, severity, tier, file="a.py", line=1, source="llm"):
    return Claim(
        agent=agent, issue=issue, file=file, line=line, severity=severity,
        evidence=[Evidence(tier=tier, text="e")], confidence=0.8, tier=tier,
        source=source,
    )


def conflict(claim, opponent):
    return {"claims": [claim, opponent], "file": claim.file, "line": claim.line,
            "type": "disputed"}


# --- 1. similarity / dedup detection -----------------------------------
def test_exact_match_is_redundant():
    assert _is_redundant("SQL injection in login", ["SQL injection in login"]) is True


def test_punctuation_only_difference_is_redundant():
    a = "sql injection risk in login query is high severity tier one"
    b = "SQL injection risk in login query is high severity, tier one."
    assert _similarity(a, b) == pytest.approx(1.0)
    assert _is_redundant(b, [a]) is True


def test_distinct_argument_is_not_redundant():
    a = "The charge is command injection at app.py:1 with T1 evidence."
    b = "No corroborating T1/T2 evidence exists, so severity should not escalate."
    assert _similarity(a, b) < 0.75
    assert _is_redundant(b, [a]) is False


def test_empty_statement_is_redundant():
    assert _is_redundant("   ", ["anything"]) is True


# --- 2. prompt tuning ---------------------------------------------------
def test_prompts_instruct_against_repetition():
    claim = mk("security", "sql injection", 5, 1, source="tool")
    opponent = mk("pragmatist", "sql injection", 1, 4)
    for prompt in (
        _build_prosecution_prompt(claim, opponent, ["prior point"]),
        _build_defense_prompt(claim, opponent, ["prior point"]),
    ):
        assert _NO_REPEAT_RULE in prompt
        assert "prior point" in prompt


def test_prompts_have_no_history_block_when_first_round():
    claim = mk("security", "sql injection", 5, 1)
    opponent = mk("pragmatist", "sql injection", 1, 4)
    assert "ALREADY made" not in _build_prosecution_prompt(claim, opponent, [])


# --- 3. clean termination in run_debate ---------------------------------
@pytest.mark.asyncio
async def test_debate_converges_when_round_is_redundant(monkeypatch):
    claim = mk("security", "sql injection", 5, 1, source="tool")
    opponent = mk("pragmatist", "sql injection", 1, 4)

    pro = "The charge is command injection at a.py:1 backed by T1 tool evidence."
    deff = "The argument is mitigated because the command is a fixed constant."

    async def fake_round(claim, opponent, round_no, assessment=None,
                         prior_pro=None, prior_def=None, snippet=""):
        return pro, deff, True  # identical every round

    monkeypatch.setattr(debate_mod, "_debate_round", fake_round)

    result = await run_debate([conflict(claim, opponent)], pr=None)
    assert len(result) == 1
    assert result[0].rounds == 1  # redundant 2nd round discarded, not looped
    assert result[0].supporting == pro
    assert result[0].opposing == deff


@pytest.mark.asyncio
async def test_debate_accepts_genuinely_new_round(monkeypatch):
    claim = mk("security", "sql injection", 5, 1, source="tool")
    opponent = mk("pragmatist", "sql injection", 1, 4)

    turns = [
        ("Charge: command injection at a.py:1 with T1 evidence.",
         "Defense: the command is a fixed constant, so risk is limited."),
        ("New evidence: gitleaks confirms a leaked token reachable from the sink.",
         "Concession: the leaked secret escalates impact; fix before merge."),
    ]

    async def fake_round(claim, opponent, round_no, assessment=None,
                         prior_pro=None, prior_def=None, snippet=""):
        return turns[round_no][0], turns[round_no][1], True

    monkeypatch.setattr(debate_mod, "_debate_round", fake_round)

    result = await run_debate([conflict(claim, opponent)], pr=None)
    assert result[0].rounds == 2
    assert "gitleaks" in result[0].supporting
    assert "Concession" in result[0].opposing


# --- 3b. retry-on-redundancy inside the LLM path ------------------------
@pytest.mark.asyncio
async def test_llm_round_retries_when_draft_repeats(monkeypatch):
    claim = mk("security", "sql injection", 5, 1, source="tool")
    opponent = mk("pragmatist", "sql injection", 1, 4)

    prior_pro = ["Original prosecution argument about the injection sink."]
    prior_def = ["Original defense argument about the fixed command."]

    calls: list[str] = []

    class FakeLLM:
        _use_mock = False
        _provider = "openai"

        async def generate(self, system, user):
            calls.append(user)
            if len(calls) == 1:
                return {"claims": [{"issue": prior_pro[0]}]}  # redundant
            if len(calls) == 2:
                return {"claims": [{"issue": "New: semgrep rule S123 confirms the tainted sink."}]}
            return {"claims": [{"issue": "Defense: admin-only reachable path limits impact."}]}

    monkeypatch.setattr(debate_mod, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(debate_mod, "_LLM_AVAILABLE", True)

    pro, deff, progressed = await debate_mod._llm_debate_round(
        claim, opponent, 1, prior_pro, prior_def
    )

    assert pro.startswith("New:")
    assert deff.startswith("Defense:")
    assert progressed is True
    assert "NEW evidence" in calls[1]  # nudge applied on the retry
