"""LLM-assisted taint specification inference — inspired by IRIS.

When static analyzers miss a vulnerability, this module:
1. Extracts candidate source/sink pairs from the code using pattern matching.
2. Uses the LLM (when available) to infer whether a taint flow exists.
3. Returns additional FindingAssessment objects for flows the scanner missed.

This directly addresses the gap identified in the IRIS paper:
static analyzers miss vulnerabilities when they lack taint specifications
for library methods. The LLM infers those specs from code context.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from patchcourt.agents.schemas import Evidence, FindingAssessment
from patchcourt.runtime_llm_config import get_runtime_config

logger = logging.getLogger("patchcourt.taint")

try:
    from patchcourt.llm import get_llm
    _LLM_AVAILABLE = True
except Exception:
    _LLM_AVAILABLE = False


# ---------------------------------------------------------------------------
# Source / Sink pattern catalog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaintSpec:
    id: str
    description: str
    source_patterns: tuple[str, ...]
    sink_patterns: tuple[str, ...]
    cwe: str = ""
    severity: int = 4


_TAINT_SPECS: list[TaintSpec] = [
    TaintSpec(
        id="TAINT-SQL",
        description="User-controlled data flows into SQL query construction",
        source_patterns=(
            r"\brequest\.(args|form|json|data|values|get|post)\b",
            r"\binput\s*\(",
            r"\bsys\.argv\b",
            r"\bos\.environ\b",
        ),
        sink_patterns=(
            r"(?i)(execute|query|cursor)\s*\(\s*[^,)]*\+",
            r"(?i)['\"]select\b[^'\"]*['\"]?\s*\+",
            r"(?i)f['\"].*select\b",
        ),
        cwe="CWE-89",
        severity=5,
    ),
    TaintSpec(
        id="TAINT-CMD",
        description="User-controlled data flows into shell command execution",
        source_patterns=(
            r"\brequest\.(args|form|json|data|values|get|post)\b",
            r"\binput\s*\(",
            r"\bsys\.argv\b",
        ),
        sink_patterns=(
            r"\bsubprocess\.(call|run|Popen)\b",
            r"\bos\.(system|popen|execv)\b",
            r"\beval\s*\(",
        ),
        cwe="CWE-78",
        severity=5,
    ),
    TaintSpec(
        id="TAINT-PATH",
        description="User-controlled data flows into file path operations",
        source_patterns=(
            r"\brequest\.(args|form|json|data|values|get|post)\b",
            r"\binput\s*\(",
        ),
        sink_patterns=(
            r"\bopen\s*\(",
            r"\bos\.path\.(join|exists|isfile)\b",
            r"\bpathlib\.Path\b",
        ),
        cwe="CWE-22",
        severity=4,
    ),
    TaintSpec(
        id="TAINT-XSS",
        description="User-controlled data flows into HTML/template rendering without escaping",
        source_patterns=(
            r"\brequest\.(args|form|json|data|values|get|post)\b",
        ),
        sink_patterns=(
            r"\brender_template_string\b",
            r"\bMarkup\s*\(",
            r"(?i)innerHTML\s*=",
            r"(?i)document\.write\s*\(",
        ),
        cwe="CWE-79",
        severity=4,
    ),
]


# ---------------------------------------------------------------------------
# Pattern-based source/sink extraction
# ---------------------------------------------------------------------------

@dataclass
class TaintFlow:
    spec: TaintSpec
    file: str
    source_line: int
    sink_line: int
    source_text: str
    sink_text: str
    confidence: float = 0.5


def _find_lines_matching(content: str, patterns: tuple[str, ...]) -> list[tuple[int, str]]:
    """Return (line_number, line_text) for lines matching any pattern."""
    results: list[tuple[int, str]] = []
    for i, line in enumerate(content.splitlines(), start=1):
        for pat in patterns:
            if re.search(pat, line):
                results.append((i, line.strip()))
                break
    return results


def extract_candidate_flows(
    file_contents: dict[str, str],
    known_findings: list[FindingAssessment] | None = None,
) -> list[TaintFlow]:
    """Extract candidate taint flows from file contents.

    Skips flows already covered by existing findings to avoid duplicates.
    """
    known_locs: set[tuple[str, int]] = set()
    for fa in (known_findings or []):
        known_locs.add((fa.file, fa.line))

    flows: list[TaintFlow] = []
    for fname, content in file_contents.items():
        for spec in _TAINT_SPECS:
            sources = _find_lines_matching(content, spec.source_patterns)
            sinks = _find_lines_matching(content, spec.sink_patterns)
            if not sources or not sinks:
                continue
            # Pair each source with the nearest sink below it
            for src_line, src_text in sources:
                for sink_line, sink_text in sinks:
                    if sink_line <= src_line:
                        continue
                    if (fname, sink_line) in known_locs:
                        continue
                    # Only flag if within 50 lines (same function heuristic)
                    if sink_line - src_line > 50:
                        continue
                    flows.append(TaintFlow(
                        spec=spec,
                        file=fname,
                        source_line=src_line,
                        sink_line=sink_line,
                        source_text=src_text,
                        sink_text=sink_text,
                        confidence=0.6,
                    ))
    return flows


# ---------------------------------------------------------------------------
# LLM taint spec inference
# ---------------------------------------------------------------------------

_TAINT_SYSTEM = (
    "You are a security analyst specializing in taint analysis. "
    "Given a code snippet with a potential source and sink, determine if "
    "user-controlled data can flow from the source to the sink without sanitization. "
    "Respond ONLY as JSON: "
    '{\"taint_flow\": true/false, \"confidence\": 0.0-1.0, \"explanation\": \"<1 sentence>\"}'
)


async def _llm_confirm_taint(flow: TaintFlow, snippet: str) -> tuple[bool, float, str]:
    """Use LLM to confirm whether a taint flow is real."""
    runtime_cfg = get_runtime_config()
    use_llm = (
        not runtime_cfg.use_mock_llm
        and runtime_cfg.provider != "mock"
        and _LLM_AVAILABLE
    )
    if not use_llm:
        return True, flow.confidence, "Pattern-based detection (LLM offline)"

    try:
        llm = get_llm()
        if llm._use_mock:
            return True, flow.confidence, "Pattern-based detection (mock LLM)"

        prompt = (
            f"Spec: {flow.spec.description} ({flow.spec.cwe})\n"
            f"Source (line {flow.source_line}): {flow.source_text}\n"
            f"Sink (line {flow.sink_line}): {flow.sink_text}\n\n"
            f"Code context:\n```\n{snippet}\n```\n\n"
            "Is there an unsanitized taint flow from source to sink?"
        )
        resp = await llm.generate(_TAINT_SYSTEM, prompt)
        raw = resp.get("raw", "") or ""
        # Parse JSON from response
        m = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if m:
            import json
            try:
                data = json.loads(m.group())
                return (
                    bool(data.get("taint_flow", True)),
                    float(data.get("confidence", 0.6)),
                    str(data.get("explanation", ""))[:200],
                )
            except Exception:
                pass
        return True, 0.5, "LLM response unparseable; defaulting to flagged"
    except Exception as e:
        logger.warning("LLM taint inference failed: %s", e)
        return True, flow.confidence, "Pattern-based detection (LLM error)"


def _snippet_around(content: str, line: int, context: int = 5) -> str:
    lines = content.splitlines()
    start = max(0, line - 1 - context)
    end = min(len(lines), line + context)
    return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))


async def infer_missed_findings(
    file_contents: dict[str, str],
    existing_assessments: list[FindingAssessment],
) -> list[FindingAssessment]:
    """Infer taint flows that static analyzers missed.

    Returns new FindingAssessment objects (tool='taint-inference') for
    flows not already covered by existing assessments.
    """
    flows = extract_candidate_flows(file_contents, existing_assessments)
    if not flows:
        return []

    new_assessments: list[FindingAssessment] = []
    seen: set[tuple[str, int]] = set()

    for flow in flows:
        key = (flow.file, flow.sink_line)
        if key in seen:
            continue

        content = file_contents.get(flow.file, "")
        snippet = _snippet_around(content, flow.sink_line)
        confirmed, confidence, explanation = await _llm_confirm_taint(flow, snippet)

        if not confirmed or confidence < 0.4:
            continue

        seen.add(key)
        new_assessments.append(FindingAssessment(
            tool="taint-inference",
            file=flow.file,
            line=flow.sink_line,
            rule=flow.spec.id,
            message=(
                f"{flow.spec.description}: taint flow from line {flow.source_line} "
                f"({flow.source_text[:60]}) to line {flow.sink_line} ({flow.sink_text[:60]})"
            ),
            severity=flow.spec.severity,
            category="security",
            status="UNCERTAIN",
            rationale=(
                f"LLM-inferred taint flow ({flow.spec.cwe}). {explanation} "
                f"Confidence: {confidence:.0%}. Requires human verification."
            ),
            corroborated=False,
            corroborating_tools=[],
            policies=[],
            contextual_priority="high" if flow.spec.severity >= 4 else "medium",
            contextual_action="human_review",
            evidence=[
                Evidence(
                    tier=3,
                    text=f"[taint-inference] {flow.spec.id}: {flow.spec.description} "
                         f"source=line {flow.source_line}, sink=line {flow.sink_line}",
                ),
                Evidence(
                    tier=5,
                    text=f"LLM taint confirmation: {explanation} (confidence {confidence:.0%})",
                ),
            ],
            fp_fn_root_cause="Missing Cases",
            fp_fn_explanation=(
                "Static analyzer lacked taint specification for this source/sink pair; "
                "inferred by LLM from code context."
            ),
            fault_correlation="high" if flow.spec.severity >= 4 else "medium",
        ))

    if new_assessments:
        logger.info("taint-inference: %d new candidate flows found", len(new_assessments))
    return new_assessments
