"""Evidence-grounded adjudication of static-analysis findings.

Implements the six PatchCourt enhancements: finding validation (E1),
repository-aware rule adjudication (E2), cross-tool correlation (E3),
contextual prioritisation (E4), and the building blocks consumed by the
evidence-backed debate and deterministic judge (E5) and by the benchmark
harness (E6).
"""
from patchcourt.adjudication.contextual import assess_context, summarize
from patchcourt.adjudication.correlate import (
    correlate_findings,
    correlation_index,
    corroborating_tools,
)
from patchcourt.adjudication.rules import (
    RULE_CATALOG,
    Policy,
    RuleInfo,
    category_for,
    load_repository_policies,
    match_policies,
    rule_for,
)
from patchcourt.adjudication.validator import (
    FindingValidator,
    added_line_numbers,
    touched_lines,
    validate_findings,
)

__all__ = [
    "RULE_CATALOG",
    "Policy",
    "RuleInfo",
    "FindingValidator",
    "assess_context",
    "summarize",
    "correlate_findings",
    "correlation_index",
    "corroborating_tools",
    "category_for",
    "load_repository_policies",
    "match_policies",
    "rule_for",
    "added_line_numbers",
    "touched_lines",
    "validate_findings",
]
