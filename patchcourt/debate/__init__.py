"""Debate module — conflict detection and bounded debate."""
from patchcourt.debate.conflict import detect_conflicts
from patchcourt.debate.debate import run_debate

__all__ = ["detect_conflicts", "run_debate"]