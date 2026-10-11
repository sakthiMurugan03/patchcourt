"""Cross-tool evidence correlation (Enhancement 3).

Clusters raw tool findings that refer to the same location so PatchCourt can
distinguish genuine agreement across independent tools from a single tool
repeating itself, and surface disagreements instead of silently merging them.
"""
from __future__ import annotations

import dataclasses
from collections import defaultdict

from patchcourt.agents.schemas import CorrelationGroup
from patchcourt.tools.base import Finding


def _finding_dict(f: Finding) -> dict:
    return dataclasses.asdict(f)


def correlate_findings(findings: list[Finding]) -> list[CorrelationGroup]:
    """Group findings by (file, line) and classify their relationship."""
    grouped: dict[tuple[str, int], list[Finding]] = defaultdict(list)
    for f in findings:
        grouped[(f.file, int(f.line or 0))].append(f)

    groups: list[CorrelationGroup] = []
    for (file, line), fs in sorted(grouped.items()):
        tools = sorted({f.tool for f in fs})
        severities = sorted({f.severity for f in fs})
        if len(tools) >= 2:
            relationship = "agreement"
        elif len(fs) >= 2:
            relationship = "duplicate"
        else:
            relationship = "solo"
        groups.append(
            CorrelationGroup(
                file=file,
                line=line,
                tools=tools,
                findings=[_finding_dict(f) for f in fs],
                relationship=relationship,
                severity_range=severities,
                disputed=len(severities) >= 2,
            )
        )
    return groups


def correlation_index(groups: list[CorrelationGroup]) -> dict[tuple[str, int], CorrelationGroup]:
    return {(g.file, int(g.line or 0)): g for g in groups}


def corroborating_tools(group: CorrelationGroup | None, tool: str) -> list[str]:
    """Distinct tools that independently flagged the same location."""
    if group is None:
        return []
    return [t for t in group.tools if t != tool]
