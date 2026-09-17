"""Bundled demo PR — an intentionally insecure diff for keyless demos."""
from __future__ import annotations

from patchcourt.agents.schemas import PRContext

_DEMO_FILES: dict[str, str] = {
    "app.py": (
        "import subprocess\n"
        "import os\n"
        "\n"
        "def deploy(command):\n"
        "    subprocess.call(command, shell=True)\n"
        "\n"
        "def lookup(user_id):\n"
        "    sql = \"SELECT * FROM users WHERE id = \" + user_id\n"
        "    return sql\n"
        "\n"
        "API_TOKEN = \"sk-live-6fa3c0d9a1b2\"\n"
    ),
    "helpers.py": (
        "def retry(fn, times=3):\n"
        "    for _ in range(times):\n"
        "        try:\n"
        "            return fn()\n"
        "        except Exception:\n"
        "            pass\n"
        "    return None\n"
    ),
}

_DEMO_PATCHES: dict[str, str] = {
    "app.py": "\n".join(f"+{line}" if line.strip() else line for line in _DEMO_FILES["app.py"].splitlines()),
    "helpers.py": "\n".join(f"+{line}" if line.strip() else line for line in _DEMO_FILES["helpers.py"].splitlines()),
}

_DEMO_TITLE = "Demo: add deployment + user lookup endpoints"
_DEMO_BODY = (
    "Live demo PR used by `python -m patchcourt review --demo`. "
    "Contains intentionally insecure patterns so the Evidence Engine "
    "produces tiered, tool-backed findings offline."
)


def demo_pr() -> PRContext:
    return PRContext(
        owner="patchcourt",
        repo="demo",
        pr_number=1337,
        title=_DEMO_TITLE,
        body=_DEMO_BODY,
        diff="\n".join(f"diff --git a/{k} b/{k}\n" + v for k, v in _DEMO_PATCHES.items()),
        file_contents=_DEMO_FILES,
        patches=_DEMO_PATCHES,
        changed_files=[{"filename": k, "patch": v} for k, v in _DEMO_PATCHES.items()],
        rag_query=_DEMO_TITLE,
    )