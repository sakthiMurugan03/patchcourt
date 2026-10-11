"""Code-context grounding and plain-English verdict summary for the debate.

Covers the additions requested for the /debate UI:
  1. the target file's code snippet is extracted and injected into prompts,
  2. both agents are told to cite real identifiers from that snippet,
  3. debate transcripts gain ``code_snippet`` + ``verdict_summary`` keys while
     keeping the existing keys intact.
"""
import pytest

from patchcourt.agents.schemas import Claim, Evidence, PRContext
from patchcourt.debate import debate as debate_mod
from patchcourt.debate.debate import (
    _extract_code_snippet,
    _fallback_verdict_summary,
    _snippet_identifiers,
    _build_prosecution_prompt,
    _build_defense_prompt,
    run_debate,
)
from patchcourt.judge.scoring import build_report
from patchcourt.llm import reset_llm
from patchcourt.runtime_llm_config import reset_runtime_config, update_runtime_config


INVITE = (
    "import subprocess\n"
    "import os\n"
    "\n"
    "def deploy(command):\n"
    "    subprocess.call(command, shell=True)\n"
    "\n"
    "def lookup(user_id):\n"
    '    sql = "SELECT * FROM users WHERE id = " + user_id\n'
    "    return sql\n"
    "\n"
    'API_TOKEN = "sk-live-6fa3c0d9a1b2"\n'
)


@pytest.fixture(autouse=True)
def _mock_llm():
    reset_runtime_config()
    update_runtime_config(use_mock_llm=True)
    reset_llm()
    yield


def mk(agent, issue, severity, tier, file="app.py", line=5, source="llm"):
    return Claim(
        agent=agent, issue=issue, file=file, line=line, severity=severity,
        evidence=[Evidence(tier=tier, text="e")], confidence=0.8, tier=tier,
        source=source,
    )


# --- code snippet extraction -------------------------------------------
def test_extract_snippet_centers_on_line_with_numbers():
    snippet = _extract_code_snippet({"app.py": INVITE}, "app.py", 5, context=5)
    assert snippet.startswith("   1: import subprocess")
    assert "   5:     subprocess.call(command, shell=True)" in snippet
    assert snippet.count("\n") == 9  # 10 lines total (lines 1-10)


def test_extract_snippet_defaults_to_first_lines_when_line_unknown():
    snippet = _extract_code_snippet({"app.py": INVITE}, "app.py", 0)
    assert snippet.startswith("   1: import subprocess")


def test_extract_snippet_missing_file_is_empty():
    assert _extract_code_snippet({"app.py": INVITE}, "missing.py", 3) == ""
    assert _extract_code_snippet(None, "app.py", 3) == ""


def test_snippet_identifiers_finds_real_names():
    snippet = _extract_code_snippet({"app.py": INVITE}, "app.py", 11, context=10)
    ids = _snippet_identifiers(snippet)
    assert "subprocess" in ids
    assert "API_TOKEN" in ids


# --- prompts are grounded in code --------------------------------------
def test_prompts_include_snippet_and_identifier_instruction():
    claim = mk("security", "Command execution with shell=True", 5, 1, source="tool")
    opponent = mk("pragmatist", "Shell usage acceptable", 2, 5)
    snippet = _extract_code_snippet({"app.py": INVITE}, "app.py", 5)
    for prompt in (
        _build_prosecution_prompt(claim, opponent, [], snippet),
        _build_defense_prompt(claim, opponent, [], snippet),
    ):
        assert "subprocess.call(command, shell=True)" in prompt
        assert "actual variable names" in prompt


def test_prompts_without_snippet_have_no_code_block():
    claim = mk("security", "issue", 5, 1)
    opponent = mk("pragmatist", "issue", 2, 5)
    assert "Relevant code from the target file" not in _build_prosecution_prompt(
        claim, opponent, []
    )


# --- fallback verdict summary ------------------------------------------
def test_fallback_summary_is_plain_english_with_action_tag():
    claim = mk("security", "Command execution with shell=True", 5, 1, source="tool")
    snippet = _extract_code_snippet({"app.py": INVITE}, "app.py", 5)
    summary = _fallback_verdict_summary(claim, snippet)
    assert summary.startswith("⚠️ Action Required:")
    assert "subprocess" in summary
    assert "shlex.quote()" in summary


def test_fallback_summary_low_severity_is_a_note():
    claim = mk("quality", "unused import", 1, 5)
    assert _fallback_verdict_summary(claim, "").startswith("ℹ️ Note:")


@pytest.mark.asyncio
async def test_generate_verdict_summary_prefers_llm(monkeypatch):
    captured = {}

    class FakeLLM:
        _use_mock = False
        _provider = "openai"

        async def generate(self, system, user):
            captured["user"] = user
            return {"claims": [{"issue": "⚠️ Action Required: sanitize subprocess.call input."}]}

    monkeypatch.setattr(debate_mod, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(debate_mod, "_LLM_AVAILABLE", True)
    update_runtime_config(provider="openai", use_mock_llm=False)

    claim = mk("security", "Command execution with shell=True", 5, 1, source="tool")
    opponent = mk("pragmatist", "trusted input", 2, 5)
    snippet = _extract_code_snippet({"app.py": INVITE}, "app.py", 5)

    summary = await debate_mod._generate_verdict_summary(
        claim, opponent, "pro", "con", snippet
    )
    assert summary == "⚠️ Action Required: sanitize subprocess.call input."
    assert "subprocess.call(command, shell=True)" in captured["user"]


# --- run_debate integration --------------------------------------------
@pytest.mark.asyncio
async def test_run_debate_attaches_snippet_and_summary():
    claim = mk("security", "Command execution with shell=True", 5, 1, source="tool")
    opponent = mk("pragmatist", "Shell usage acceptable", 2, 5)
    pr = PRContext(file_contents={"app.py": INVITE})

    result = await run_debate([{"claims": [claim, opponent]}], pr)
    assert len(result) == 1
    d = result[0]
    assert "subprocess.call(command, shell=True)" in d.code_snippet
    assert d.verdict_summary.startswith("⚠️ Action Required:")
    assert "subprocess" in d.verdict_summary


@pytest.mark.asyncio
async def test_run_debate_without_pr_still_returns_summary():
    claim = mk("security", "SQL built by string concatenation", 5, 1, source="tool")
    opponent = mk("pragmatist", "trusted input", 2, 5)

    result = await run_debate([{"claims": [claim, opponent]}], pr=None)
    assert result[0].code_snippet == ""
    assert result[0].verdict_summary  # still a plain-English takeaway


# --- report schema stays backward compatible ---------------------------
def test_build_report_exposes_new_keys_and_keeps_old_ones():
    claim = mk("security", "Command execution with shell=True", 5, 1, source="tool")
    debated = debate_mod.DebatedClaim(
        claim=claim,
        supporting="pro",
        opposing="con",
        rounds=1,
        code_snippet="   1: import subprocess",
        verdict_summary="⚠️ Action Required: fix subprocess usage.",
    )
    report = build_report("https://github.com/a/b/pull/1", [claim], [debated])
    t = report.debate_transcripts[0]
    for key in ("file", "issue", "supporting", "opposing", "rounds"):
        assert key in t
    assert t["code_snippet"] == "   1: import subprocess"
    assert t["verdict_summary"] == "⚠️ Action Required: fix subprocess usage."
