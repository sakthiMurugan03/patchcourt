"""Base abstractions for analysis-tool adapters."""
from __future__ import annotations

import dataclasses
import logging
import os
import shutil
import tempfile
from typing import Protocol

logger = logging.getLogger("patchcourt.tools")


@dataclasses.dataclass
class Finding:
    """A raw finding produced by an analysis tool."""

    tool: str
    file: str
    line: int
    message: str
    severity: int = 3
    rule: str = ""


class ToolAdapter(Protocol):
    """Interface every adapter implements: ``run(changed_files) -> [Finding]``."""

    name: str
    binary: str | None

    def available(self) -> bool: ...

    async def run(self, file_contents: "dict[str, str]") -> list[Finding]: ...


def materialize(file_contents: dict[str, str]):
    """Write in-memory file contents to a temp directory (context manager)."""
    d = tempfile.mkdtemp(prefix="patchcourt_")
    try:
        for fname, content in file_contents.items():
            path = os.path.join(d, fname.lstrip("/"))
            os.makedirs(os.path.dirname(path) or d, exist_ok=True)
            with open(path, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(content)
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _binary_available(binary: str | None) -> bool:
    return bool(binary) and shutil.which(binary) is not None