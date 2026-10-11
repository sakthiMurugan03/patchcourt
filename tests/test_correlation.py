"""Cross-tool correlation tests (Enhancement 3)."""
from patchcourt.adjudication.correlate import (
    correlation_index,
    correlate_findings,
    corroborating_tools,
)
from patchcourt.tools.base import Finding


def f(tool, file="a.py", line=5, sev=5, msg="boom", rule="R"):
    return Finding(tool=tool, file=file, line=line, message=msg, severity=sev, rule=rule)


def test_two_tools_agree_is_agreement():
    groups = correlate_findings([f("semgrep"), f("bandit")])
    assert len(groups) == 1
    assert groups[0].relationship == "agreement"
    assert groups[0].tools == ["bandit", "semgrep"]
    assert not groups[0].disputed


def test_same_tool_twice_is_duplicate_not_corroboration():
    groups = correlate_findings([f("semgrep"), f("semgrep")])
    assert groups[0].relationship == "duplicate"


def test_single_finding_is_solo():
    groups = correlate_findings([f("semgrep")])
    assert groups[0].relationship == "solo"


def test_disagreement_disputed():
    groups = correlate_findings([f("semgrep", sev=5), f("bandit", sev=2)])
    assert groups[0].disputed
    assert groups[0].severity_range == [2, 5]


def test_group_split_by_line():
    groups = correlate_findings([f("semgrep", line=5), f("bandit", line=9)])
    assert len(groups) == 2


def test_corroborating_tools_excludes_self():
    groups = correlate_findings([f("semgrep"), f("bandit")])
    index = correlation_index(groups)
    group = index[("a.py", 5)]
    assert corroborating_tools(group, "semgrep") == ["bandit"]
    assert corroborating_tools(group, "bandit") == ["semgrep"]
    assert corroborating_tools(None, "semgrep") == []