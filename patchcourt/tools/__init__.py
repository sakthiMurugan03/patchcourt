"""Tool adapters — swappable static-analysis back-ends for the Evidence Engine."""
from __future__ import annotations

from patchcourt.tools.base import Finding, ToolAdapter, materialize
from patchcourt.tools.registry import enabled_adapters, run_enabled_tools
from patchcourt.tools.synthetic import SyntheticAdapter

__all__ = [
    "Finding",
    "ToolAdapter",
    "materialize",
    "enabled_adapters",
    "run_enabled_tools",
    "SyntheticAdapter",
]