"""Bounded evidence-gated debate. Max 2 rounds, RAG-fresh rebuttals.

The debate is *anti-redundant*: before a turn is accepted it is compared
against every statement already made in this session, prompt-side history is
fed back to the agents so they know what has been said, and a round that adds
no new argument terminates the debate cleanly instead of looping.
"""
from __future__ import annotations

import logging
import re

from patchcourt.agents.schemas import Claim, DebatedClaim
from patchcourt.config import settings
from patchcourt.runtime_llm_config import get_runtime_config

logger = logging.getLogger("patchcourt.debate")

try:
    from patchcourt.llm import get_llm
    _LLM_AVAILABLE = True
except Exception:
    _LLM_AVAILABLE = False


# --- Redundancy control ------------------------------------------------
# Lexical similarity is deliberately dependency-free: token Jaccard over the
# normalized statements. Identical text scores 1.0; a substantially reworded
# restatement still scores high enough to be caught.
_REDUNDANCY_THRESHOLD = 0.75

# Explicit instruction injected into both system prompts and per-turn user
# prompts so the agents stop restating settled points.
_NO_REPEAT_RULE = (
    "Do not repeat previous arguments. If an argument has already been stated, "
    "introduce new evidence or move directly to closing remarks."
)

_PROSECUTION_SYSTEM = (
    "You are the PROSECUTION in a code review debate. State the charge clearly. "
    + _NO_REPEAT_RULE
)
_DEFENSE_SYSTEM = (
    "You are the DEFENSE in a code review debate. Make a real rebuttal. "
    + _NO_REPEAT_RULE
)

_NEW_ARGUMENT_NUDGE = (
    "\n\nIMPORTANT: Your previous draft merely repeated an argument already "
    "made in this debate. Do not restate it. Introduce NEW evidence, address "
    "the opponent's latest point, or move directly to closing remarks."
)

_WORD_RE = re.compile(r"[^a-z0-9 ]+")


def _normalize(text: str) -> str:
    return _WORD_RE.sub(" ", (text or "").lower()).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if len(t) > 2}


def _similarity(a: str, b: str) -> float:
    """Token Jaccard similarity in [0, 1]; 1.0 for exact normalized match."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _is_redundant(text: str, prior: list[str], threshold: float = _REDUNDANCY_THRESHOLD) -> bool:
    """True if ``text`` is empty or too similar to anything already said."""
    if not (text or "").strip():
        return True
    return any(_similarity(text, p) >= threshold for p in prior if (p or "").strip())


def _history_block(prior: list[str]) -> str:
    """Render the already-said statements as an explicit avoid-list."""
    seen = [p for p in prior if (p or "").strip()]
    if not seen:
        return ""
    lines = "\n".join(f"- {p}" for p in seen)
    return (
        "\n\nStatements ALREADY made in this debate (do NOT repeat or paraphrase these):\n"
        f"{lines}\n"
        f"{_NO_REPEAT_RULE} Advance the argument by adding new evidence or "
        "addressing the opponent's latest point."
    )


# --- Code context ------------------------------------------------------
# The agents are grounded in the *actual* target code, not just the rule
# text, so their arguments name real identifiers instead of vague jargon.
_SNIPPET_CONTEXT_LINES = 5
_SNIPPET_MAX_CHARS = 1400
_LINE_PREFIX_RE = re.compile(r"^\s*\d+:\s?", re.M)
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import\s+([\w,\s]+)|import\s+([\w.,\s]+))", re.M
)
_CALL_RE = re.compile(r"\b([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)\s*\(")
_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=", re.M)

_PY_KEYWORDS = {
    "the", "and", "for", "not", "with", "this", "that", "from", "import",
    "def", "class", "return", "if", "else", "elif", "while", "try", "except",
    "finally", "with", "as", "in", "is", "lambda", "yield", "raise", "pass",
    "none", "true", "false", "self", "str", "int", "list", "dict", "set",
    "len", "range", "print", "call", "user", "line", "code", "file", "risk",
}


def _extract_code_snippet(
    file_contents: dict | None,
    file: str,
    line: int,
    context: int = _SNIPPET_CONTEXT_LINES,
    max_chars: int = _SNIPPET_MAX_CHARS,
) -> str:
    """Return the target file's code around ``line`` with line numbers.

    Falls back to the first 10 lines when the line is unknown or out of range,
    so the agents always get *some* concrete code to reference.
    """
    content = (file_contents or {}).get(file)
    if not content:
        return ""
    lines = content.splitlines()
    if not lines:
        return ""

    if line and 0 < line <= len(lines):
        start = max(0, line - 1 - context)
        end = min(len(lines), line + context)
    else:
        start, end = 0, min(len(lines), 10)

    rendered = [f"{i + 1:>4}: {lines[i]}" for i in range(start, end)]
    snippet = "\n".join(rendered)
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rstrip() + "\n... (truncated)"
    return snippet


def _snippet_identifiers(snippet: str, limit: int = 6) -> list[str]:
    """Pull notable identifiers (imports, calls, assignments) out of a snippet."""
    if not snippet:
        return []
    body = _LINE_PREFIX_RE.sub("", snippet)
    found: list[str] = []

    def _add(name: str) -> None:
        name = (name or "").strip()
        if (
            name
            and len(name) > 2
            and name.lower() not in _PY_KEYWORDS
            and name not in found
        ):
            found.append(name)

    for m in _IMPORT_RE.finditer(body):
        for part in (m.group(2), m.group(3)):
            if part:
                for name in re.split(r"[,\s]+", part):
                    _add(name)
        _add(m.group(1))
    for m in _CALL_RE.finditer(body):
        _add(m.group(1).split(".")[-1])
    for m in _ASSIGN_RE.finditer(body):
        _add(m.group(1))
    return found[:limit]


def _code_context_block(snippet: str) -> str:
    """Prompt block that forces the agent to cite real identifiers."""
    if not snippet:
        return ""
    return (
        "\n\nRelevant code from the target file (with line numbers):\n"
        f"```\n{snippet}\n```\n"
        "Ground your argument in THIS code. Explicitly name the actual variable "
        "names, function calls, or import statements you can see above (for "
        "example `subprocess.call(..., shell=True)` or `API_TOKEN`). Do not speak "
        "in generic security jargon that could apply to any codebase."
    )


# --- Plain-English verdict summary -------------------------------------
_SEVERITY_TAGS = {
    1: "ℹ️ Note:",
    2: "ℹ️ Note:",
    3: "⚠️ Review Recommended:",
    4: "⚠️ Action Required:",
    5: "⚠️ Action Required:",
}

_SUMMARY_SYSTEM = (
    "You summarize a code-review debate for a busy developer in 1-2 plain-English "
    "sentences (max 45 words). Begin with an action tag — '⚠️ Action Required:', "
    "'⚠️ Review Recommended:', or 'ℹ️ Note:'. Name the actual identifiers visible "
    "in the provided code snippet (variable names, function calls, imports) and "
    "state the concrete fix. Avoid jargon and rule IDs. Respond ONLY as JSON: "
    '{"claims": [{"issue": "<summary>"}]}'
)


def _remediation_hint(issue: str) -> str:
    text = (issue or "").lower()
    if any(k in text for k in ("command", "shell", "subprocess", "os.system", "eval", "exec")):
        return "Avoid passing untrusted input to the shell — use `shlex.quote()` or `shell=False`."
    if any(k in text for k in ("sql", "injection", "query", "concatenation")):
        return "Use parameterized queries instead of building SQL from strings."
    if any(k in text for k in ("credential", "secret", "password", "token", "api key", "hardcoded")):
        return "Move secrets to environment variables or a secret manager and rotate the exposed value."
    if any(k in text for k in ("xss", "html", "escape")):
        return "Encode or escape untrusted values before rendering them."
    if any(k in text for k in ("path", "traversal", "directory")):
        return "Validate and normalize file paths before use."
    return ""


def _fallback_verdict_summary(claim: Claim, snippet: str) -> str:
    """Deterministic plain-English takeaway used offline / on LLM failure."""
    tag = _SEVERITY_TAGS.get(claim.severity, "ℹ️ Note:")
    loc = f"{claim.file}:{claim.line}" if claim.line else claim.file
    ids = _snippet_identifiers(snippet)
    if ids:
        shown = ", ".join(f"`{i}`" for i in ids[:3])
        sentence = f"{tag} {claim.issue} — involves {shown} at `{loc}`."
    else:
        sentence = f"{tag} {claim.issue} at `{loc}`."
    hint = _remediation_hint(claim.issue)
    if hint:
        sentence += f" {hint}"
    return sentence


def _build_summary_prompt(
    claim: Claim,
    opponent: Claim,
    supporting: str,
    opposing: str,
    snippet: str,
) -> str:
    loc = f"{claim.file}:{claim.line}" if claim.line else claim.file
    return (
        f"Disputed finding: {claim.issue} ({loc}, severity {claim.severity}/5, T{claim.tier}).\n"
        f"Prosecution said: {supporting or '(none)'}\n"
        f"Defense said: {opposing or '(none)'}\n"
        f"Opposing claim: {opponent.issue}\n"
        + _code_context_block(snippet)
        + "\n\nWrite the developer-facing summary now."
    )


async def _generate_verdict_summary(
    claim: Claim,
    opponent: Claim,
    supporting: str,
    opposing: str,
    snippet: str,
) -> str:
    """LLM summary when a real provider is configured, else a deterministic one."""
    runtime_cfg = get_runtime_config()
    use_llm = (
        not runtime_cfg.use_mock_llm
        and runtime_cfg.provider != "mock"
        and _LLM_AVAILABLE
    )
    if use_llm:
        try:
            llm = get_llm()
            if not llm._use_mock:
                prompt = _build_summary_prompt(claim, opponent, supporting, opposing, snippet)
                summary = (await _llm_generate_turn(_SUMMARY_SYSTEM, prompt)).strip()
                if summary:
                    return summary
        except Exception as e:
            logger.warning("verdict summary generation failed, using fallback: %s", e)
    return _fallback_verdict_summary(claim, snippet)


def _tier(tag: str) -> int:
    for t in range(1, 6):
        if f"T{t}" in tag.upper():
            return t
    return 3


def _source_label(claim: Claim) -> str:
    """Return a short label for the claim's source."""
    if claim.source == "tool":
        for e in claim.evidence:
            t = e.text.lower()
            if "bandit" in t:
                return "Bandit"
            if "semgrep" in t:
                return "Semgrep"
            if "gitleaks" in t:
                return "Gitleaks"
            if "radon" in t:
                return "Radon"
        return "Static analysis"
    return claim.agent.capitalize()


def _rule_snippet(claim: Claim) -> str:
    """Extract rule ID from evidence if available."""
    for e in claim.evidence:
        t = e.text
        import re
        m = re.search(r"\b([A-Z][A-Z0-9]{2,}|B\d{3}|SEC-\d+|[A-Z]{2,}-\d+)\b", t)
        if m:
            return f"rule {m.group(1)}"
    return "rule"


def _evidence_summary(claim: Claim) -> str:
    """Summarize the claim's evidence tiers."""
    tiers = [e.tier for e in claim.evidence]
    if not tiers:
        return "no evidence"
    best = min(tiers)
    return f"best tier T{best}"


def _build_prosecution_prompt(
    claim: Claim,
    opponent: Claim,
    prior: list[str] | None = None,
    snippet: str = "",
) -> str:
    """Build prompt for prosecution argument."""
    source = _source_label(claim)
    rule = _rule_snippet(claim)
    loc = f"{claim.file}:{claim.line}" if claim.line else claim.file
    sev_labels = {1: "info", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    sev = sev_labels.get(claim.severity, "medium")
    tier = f"T{claim.tier}"
    ev_summary = _evidence_summary(claim)

    return (
        f"You are the PROSECUTION in a code review debate. State the charge clearly.\n\n"
        f"Claim: {claim.issue}\n"
        f"Location: {loc}\n"
        f"Source: {source}\n"
        f"Severity: {claim.severity}/{sev}\n"
        f"Tier: T{claim.tier}\n"
        f"Evidence: {_evidence_summary(claim)}\n\n"
        f"Opposing claim: {opponent.issue}\n"
        f"Opposing tier: T{opponent.tier}\n\n"
        f"Write 1-2 sentences stating the charge in plain language + why it matters (the risk). "
        f"Cite the tool/rule/file:line and tier. Do NOT just restate the rule text."
        + _code_context_block(snippet)
        + _history_block(prior or [])
    )


def _build_defense_prompt(
    claim: Claim,
    opponent: Claim,
    prior: list[str] | None = None,
    snippet: str = "",
) -> str:
    """Build prompt for defense argument."""
    opp_source = _source_label(opponent)
    opp_rule = _rule_snippet(opponent)
    opp_loc = f"{opponent.file}:{opponent.line}" if opponent.line else opponent.file

    return (
        f"You are the DEFENSE in a code review debate. Make a REAL REBUTTAL.\n\n"
        f"Your claim: {claim.issue}\n"
        f"Your tier: T{claim.tier}\n"
        f"Opposing claim: {opponent.issue}\n"
        f"Opposing location: {opponent.file}:{opponent.line if opponent.line else '?'}\n"
        f"Opposing source: {opponent.source}\n"
        f"Opposing tier: T{opponent.tier}\n\n"
        f"Choose ONE of these strategies and write 1-2 sentences:\n"
        f"(a) Argue MITIGATION/CONTEXT — e.g., 'used with a fixed command, not user input, so injection risk is limited'\n"
        f"(b) Note LACK OF CORROBORATION — e.g., 'no corroborating T1/T2 evidence, so severity should not escalate'\n"
        f"(c) CONCEDE — e.g., 'finding stands; recommend fixing before merge'\n\n"
        f"DO NOT just restate the prosecution's rule text. Make a distinct argument."
        + _code_context_block(snippet)
        + _history_block(prior or [])
    )


async def _llm_generate_turn(system: str, user: str) -> str:
    """Generate a single debate statement, extracting its text."""
    llm = get_llm()
    resp = await llm.generate(system, user)
    claims = resp.get("claims") or []
    if claims:
        return claims[0].get("issue", "")
    return resp.get("raw", "")


async def _llm_debate_round(
    claim: Claim,
    opponent: Claim,
    round_no: int,
    prior_pro: list[str],
    prior_def: list[str],
    snippet: str = "",
) -> tuple[str, str, bool]:
    """Generate both sides via LLM for a debate round.

    Each side is written against the full set of statements already made in
    this session and the target file's code snippet. If a draft is redundant,
    it is regenerated once with an explicit "introduce new evidence" nudge;
    ``progressed`` reports whether the accepted round actually advanced the
    argument.
    """
    if not _LLM_AVAILABLE:
        raise RuntimeError("LLM not available")

    llm = get_llm()
    if llm._use_mock:
        raise RuntimeError("LLM is in mock mode")

    try:
        seen = list(prior_pro) + list(prior_def)

        prosecution_prompt = _build_prosecution_prompt(claim, opponent, seen, snippet)
        prosecution = await _llm_generate_turn(_PROSECUTION_SYSTEM, prosecution_prompt)
        if _is_redundant(prosecution, seen):
            prosecution = await _llm_generate_turn(
                _PROSECUTION_SYSTEM, prosecution_prompt + _NEW_ARGUMENT_NUDGE
            )

        defense_seen = seen + [prosecution]
        defense_prompt = _build_defense_prompt(claim, opponent, defense_seen, snippet)
        defense = await _llm_generate_turn(_DEFENSE_SYSTEM, defense_prompt)
        if _is_redundant(defense, defense_seen):
            defense = await _llm_generate_turn(
                _DEFENSE_SYSTEM, defense_prompt + _NEW_ARGUMENT_NUDGE
            )

        progressed = not _is_redundant(prosecution, seen) or not _is_redundant(
            defense, defense_seen
        )
        return prosecution, defense, progressed
    except Exception as e:
        logger.warning("LLM debate generation failed: %s", e)
        raise


def _assessment_status(assessment) -> str:
    return assessment.status if assessment is not None else ""


def _format_prosecution_mock(
    claim: Claim, round_no: int, assessment=None, snippet: str = ""
) -> str:
    """Format prosecution statement (mock mode)."""
    source = _source_label(claim)
    rule = _rule_snippet(claim)
    loc = f"{claim.file}:{claim.line}" if claim.line else claim.file
    sev_labels = {1: "info", 2: "low", 3: "medium", 4: "high", 5: "critical"}
    sev = sev_labels.get(claim.severity, "medium")
    tier = f"T{claim.tier}"
    status = _assessment_status(assessment)
    ids = _snippet_identifiers(snippet)
    code_ref = (
        f" The code shows {', '.join(f'`{i}`' for i in ids[:3])}." if ids else ""
    )

    if round_no == 1:
        statement = (
            f"{source} {rule} flags {claim.issue} at {loc} — "
            f"risk: {claim.issue.lower()} could lead to security/exploit issues "
            f"(severity {claim.severity}/{sev}, T{claim.tier}).{code_ref}"
        )
        if status:
            statement += f" Independent adjudication on this location: {status}."
        return statement
    else:
        statement = (
            f"R{round_no} — {source} still flags {claim.issue} at {loc}; "
            f"no new evidence reduces the risk (T{claim.tier})."
        )
        if status:
            statement += f" Adjudication: {status}."
        return statement


def _format_defense_mock(
    claim: Claim, opponent: Claim, round_no: int, assessment=None, snippet: str = ""
) -> str:
    """Format defense rebuttal (mock mode) — genuinely different from prosecution."""
    opp_source = _source_label(opponent)
    opp_rule = _rule_snippet(opponent)
    opp_loc = f"{opponent.file}:{opponent.line}" if opponent.line else opponent.file
    opp_max_tier = max((e.tier for e in opponent.evidence), default=5)
    opp_has_strong = opp_max_tier <= 2

    # Determine defense strategy based on claim properties
    claim_type = claim.issue.lower()
    has_context = any(
        "fixed" in e.text.lower() or "hardcoded" in e.text.lower() or "constant" in e.text.lower()
        for e in claim.evidence
    )
    has_corroboration = claim.corroborated or any(e.tier <= 2 for e in claim.evidence)
    status = _assessment_status(assessment)
    adjudicated = f" The independent validator also marked this location {status}." if status else ""
    ids = _snippet_identifiers(snippet)
    code_ref = f" Relevant code: {', '.join(f'`{i}`' for i in ids[:3])}." if ids else ""

    if round_no == 1:
        if opp_has_strong:
            # Opponent has strong evidence - acknowledge but contextualize
            return (
                f"{opponent.issue} at {opp_loc} is corroborated (T{opp_max_tier}). "
                f"However, the risk is mitigated because the code uses a fixed command pattern, "
                f"not dynamic user input — injection vector is limited.{code_ref}{adjudicated}"
            )
        elif has_context:
            # Argue mitigation
            return (
                f"Finding stands but severity overstated: the code uses a fixed/hardcoded value, "
                f"not user-controlled input, so injection risk is minimal.{code_ref}{adjudicated}"
            )
        elif not has_corroboration:
            # Argue lack of corroboration
            return (
                f"No T1/T2 corroborating evidence from {opponent.source} "
                f"(max tier T{opp_max_tier}); severity should not escalate beyond T{claim.tier}.{code_ref}{adjudicated}"
            )
        else:
            # Concede
            return (
                f"Finding stands — recommend fixing before merge. "
                f"No strong mitigation identified.{code_ref}{adjudicated}"
            )
    else:
        if opp_has_strong:
            return (
                f"R{round_no} — {opponent.source} still corroborates with T{opp_max_tier} evidence; "
                f"finding confirmed.{adjudicated}"
            )
        else:
            return (
                f"R{round_no} — opponent lacks T1/T2 proof (best T{opp_max_tier}); "
                f"original claim at T{claim.tier} stands without escalation.{adjudicated}"
            )


async def _debate_round(
    claim: Claim,
    opponent: Claim,
    round_no: int,
    assessment=None,
    prior_pro: list[str] | None = None,
    prior_def: list[str] | None = None,
    snippet: str = "",
) -> tuple[str, str, bool]:
    """Run a single debate round, using LLM if available.

    ``prior_pro``/``prior_def`` are the statements already accepted in this
    session; they gate redundancies and are fed back into the prompts.
    ``snippet`` is the target file's code, injected so agents cite real
    identifiers. Returns ``(supporting, opposing, progressed)``.
    """
    prior_pro = prior_pro or []
    prior_def = prior_def or []

    # Check if we should use real LLM - check runtime config for effective settings
    runtime_cfg = get_runtime_config()
    use_llm = (
        not runtime_cfg.use_mock_llm
        and runtime_cfg.provider != "mock"
        and _LLM_AVAILABLE
    )

    if use_llm:
        try:
            return await _llm_debate_round(
                claim, opponent, round_no, prior_pro, prior_def, snippet
            )
        except Exception as e:
            logger.warning("LLM debate failed, falling back to mock: %s", e)

    # Mock mode fallback — deterministic templates already advance each round.
    return (
        _format_prosecution_mock(claim, round_no, assessment, snippet),
        _format_defense_mock(claim, opponent, round_no, assessment, snippet),
        True,
    )


async def run_debate(conflicts: list[dict], pr, assessments: list | None = None) -> list[DebatedClaim]:
    """Run a bounded, anti-redundant debate over conflicting claims.

    Uses real LLM when LLM_PROVIDER != mock, falls back to improved mock templates.
    Adjudication assessments (when provided) are surfaced to both sides so the
    debate is anchored to validated evidence rather than opinions.

    Each round is checked against the statements already made: a round that
    repeats a prior argument is discarded and the debate terminates cleanly
    (converges) instead of emitting redundant turns.
    """
    aindex: dict[tuple, object] = {}
    for a in assessments or []:
        aindex[(a.file, int(a.line or 0))] = a

    file_contents = getattr(pr, "file_contents", None) or {}

    resolved: list[DebatedClaim] = []
    for conflict in conflicts:
        claim: Claim = conflict["claims"][0]
        opponent: Claim = conflict["claims"][-1]
        assessment = aindex.get((claim.file, int(claim.line or 0)))
        snippet = _extract_code_snippet(file_contents, claim.file, claim.line)
        base = DebatedClaim(
            claim=claim,
            supporting="",
            opposing="",
            rounds=0,
            code_snippet=snippet,
        )

        prior_pro: list[str] = []
        prior_def: list[str] = []
        last_supporting = ""
        last_opposing = ""

        for round_no in range(max(1, min(settings.debate_max_rounds, 2))):
            supporting, opposing, _progressed = await _debate_round(
                claim, opponent, round_no, assessment, prior_pro, prior_def, snippet
            )

            seen_for_pro = list(prior_pro) + list(prior_def)
            seen_for_def = seen_for_pro + [supporting]
            sup_redundant = _is_redundant(supporting, seen_for_pro)
            opp_redundant = _is_redundant(opposing, seen_for_def)

            # A later round that only restates earlier points adds nothing —
            # stop the debate and keep the last substantive turn.
            if round_no > 0 and sup_redundant and opp_redundant:
                logger.info(
                    "debate converged at round %d for %s:%s — no new arguments",
                    round_no, claim.file, claim.line,
                )
                break

            # Never replace a substantive turn with a redundant restatement.
            if sup_redundant and last_supporting:
                supporting = last_supporting
            if opp_redundant and last_opposing:
                opposing = last_opposing

            last_supporting, last_opposing = supporting, opposing
            prior_pro.append(supporting)
            prior_def.append(opposing)
            base.supporting = supporting
            base.opposing = opposing
            base.rounds = round_no + 1

            # Check if opponent has strong evidence to stop early
            opp_max_tier = max((e.tier for e in opponent.evidence), default=5)
            if opp_max_tier <= _tier("T2") and opp_max_tier <= 3:
                # Opponent has strong evidence — debate resolved
                base.supporting = (
                    f"R{round_no+1} — defense acknowledged; "
                    f"{_source_label(opponent)} corroborates with T{opp_max_tier} evidence."
                )
                base.opposing = (
                    f"R{round_no+1} — opponent's evidence confirmed at T{opp_max_tier}; "
                    f"no further rebuttal needed."
                )
                break

        base.verdict_summary = await _generate_verdict_summary(
            claim, opponent, base.supporting, base.opposing, snippet
        )
        resolved.append(base)
    return resolved