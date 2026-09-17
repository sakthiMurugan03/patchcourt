"""Tool registry — builds enabled adapters from config and runs them."""
from __future__ import annotations

import asyncio
import logging

from patchcourt.tools.base import Finding, materialize
from patchcourt.tools.semgrep import SemgrepAdapter
from patchcourt.tools.bandit import BanditAdapter
from patchcourt.tools.gitleaks import GitleaksAdapter
from patchcourt.tools.radon import RadonAdapter
from patchcourt.tools.synthetic import SyntheticAdapter

logger = logging.getLogger("patchcourt.tools.registry")

_ADAPTERS: dict[str, type] = {
    "semgrep": SemgrepAdapter,
    "bandit": BanditAdapter,
    "gitleaks": GitleaksAdapter,
    "radon": RadonAdapter,
    "synthetic": SyntheticAdapter,
}


def _synthetic_enabled() -> bool:
    from patchcourt.config import settings

    return settings.enable_synthetic_tools or settings.demo_mode


def enabled_adapters() -> list:
    from patchcourt.config import settings

    names = [n.strip().lower() for n in settings.enabled_tools.split(",") if n.strip()]
    adapters: list = [_ADAPTERS[n]() for n in names if n in _ADAPTERS]
    if "synthetic" not in names and _synthetic_enabled() and "synthetic" in _ADAPTERS:
        adapters.append(_ADAPTERS["synthetic"]())
    return adapters


async def run_enabled_tools(file_contents: dict[str, str]) -> list[Finding]:
    """Run every enabled adapter concurrently; missing binaries skip gracefully."""
    adapters = enabled_adapters()
    if not adapters:
        return []
    available = [a for a in adapters if a.available()]
    skipped = [a.name for a in adapters if not a.available()]
    if skipped:
        logger.info("skipping unavailable tools: %s", ", ".join(skipped))
    results = await asyncio.gather(
        *(a.run(dict(file_contents)) for a in available), return_exceptions=True
    )
    findings: list[Finding] = []
    for tool, res in zip(available, results):
        if isinstance(res, Exception):
            logger.warning("tool %s failed: %s", tool.name, res)
            continue
        findings.extend(res)
    return findings