"""SonarQube baseline — pull unresolved quality issues from a SonarQube server
and compare them against the files touched by a GitHub PR. Produces a markdown
report (and raw JSON) that maps SonarQube findings to PatchCourt evidence tiers."""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time

import httpx

from patchcourt.config import settings

logger = logging.getLogger("patchcourt.baseline")

_SCANNER_IMAGE = "sonarsource/sonar-scanner-cli:11"

# SonarQube rule severity -> suggested PatchCourt evidence tier.
# Blocker/Critical are hard static-analysis facts (T1); Major needs
# corroboration (T2); Minor/Info are weak signals (T3/T4).
_SEVERITY_TIER = {"BLOCKER": 1, "CRITICAL": 1, "MAJOR": 2, "MINOR": 3, "INFO": 4}
_ISSUE_TYPE = {"VULNERABILITY": "security", "BUG": "correctness", "CODE_SMELL": "maintainability"}


def parse_pr_url(url: str) -> tuple[str, str, int]:
    m = re.search(r"github\.com/(?P<o>[^/]+)/(?P<r>[^/]+)/pull/(?P<n>\d+)", url.strip())
    if not m:
        raise ValueError(f"Not a valid GitHub PR URL: {url}")
    return m.group("o"), m.group("r"), int(m.group("n"))


def fetch_sonar_issues(component: str, server_url: str, token: str) -> list[dict]:
    """Page through /api/issues/search over unresolved (open) issues."""
    if not token:
        raise ValueError("SONAR_TOKEN is required for the baseline comparison")
    headers = {"Authorization": f"Bearer {token}"}
    base = f"{server_url.rstrip('/')}/api/issues/search"
    issues: list[dict] = []
    page = 1
    while True:
        resp = httpx.get(
            base,
            params={"componentKeys": component, "resolved": "false", "ps": 100, "p": page},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        issues.extend(data.get("issues", []))
        paging = data.get("paging", {})
        total = int(paging.get("total", 0))
        if len(issues) >= total or len(data.get("issues", [])) == 0:
            break
        page += 1
    return issues


def fetch_pr_files(pr_url: str) -> list[dict]:
    """List changed files for a PR via the GitHub REST API."""
    owner, repo, num = parse_pr_url(pr_url)
    base = f"https://api.github.com/repos/{owner}/{repo}/pulls/{num}/files"
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    files: list[dict] = []
    page = 1
    while True:
        resp = httpx.get(base, params={"per_page": 100, "page": page}, headers=headers, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        files.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return files


def project_key_for_pr(owner: str, repo: str, num: int) -> str:
    """Per-PR SonarQube project key, namespaced so an ad-hoc scan of an
    arbitrary external repo never collides with `settings.sonar_component`
    (patchcourt's own, continuously-scanned project) or with another PR's
    scan sitting in the same SonarQube instance."""
    raw = f"pr-{owner}-{repo}-{num}".lower()
    return re.sub(r"[^a-z0-9_.:-]", "-", raw)


def _scanner_host_url(server_url: str) -> str:
    """A sibling container (launched via the host's docker.sock from inside
    the api container, or directly from the host) can never reach SonarQube
    via 'localhost' — that resolves to the sibling container itself, not
    whatever's serving SonarQube. host.docker.internal is the one address
    that reaches the host from either calling context on Docker Desktop."""
    if "localhost" in server_url or "127.0.0.1" in server_url:
        return server_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
    return server_url


def _wait_for_ce(component: str, server_url: str, token: str, timeout: float = 300) -> None:
    """Block until SonarQube's async report-processing (Compute Engine) has
    finished for this component — querying issues right after the scanner
    exits reads a report that hasn't been ingested yet and silently returns 0."""
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + timeout
    url = f"{server_url.rstrip('/')}/api/ce/component"
    while time.time() < deadline:
        try:
            resp = httpx.get(url, params={"component": component}, headers=headers, timeout=15)
            if resp.is_success:
                data = resp.json()
                if not data.get("queue") and (data.get("current") or {}).get("status") in (
                    "SUCCESS",
                    "FAILED",
                    "CANCELED",
                ):
                    return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    logger.warning("SonarQube processing for %s did not finish within %ss", component, timeout)


def run_ondemand_scan(
    file_contents: dict[str, str],
    project_key: str,
    server_url: str | None = None,
    token: str | None = None,
) -> None:
    """Scan just these files (a PR's changed files, not a full checkout) into
    a fresh per-PR SonarQube project, then block until processing completes.

    Used for PRs against a repo SonarQube has never analyzed as a whole —
    the only files we have for an arbitrary external repo are the changed
    ones (already fetched for the agent review), so this is what makes the
    SonarQube-vs-agent comparison meaningful for anything beyond patchcourt's
    own PRs. Runs as a Docker sibling container: writes into
    ``settings.sandbox_workdir`` (already bind-mounted host<->container by
    docker-compose for exactly this reason — see the sandbox runner) so the
    path resolves correctly whether this runs inside the api container or
    directly on the host.
    """
    server_url = server_url or settings.sonar_url
    token = token or settings.sonar_token
    if not token:
        raise ValueError("SONAR_TOKEN is required for an on-demand scan")
    if not file_contents:
        return

    base_dir = (settings.sandbox_workdir or "").strip() or None
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
    workdir = tempfile.mkdtemp(dir=base_dir, prefix="patchcourt_sonarscan_")
    # mkdtemp defaults to 0700 (owner-only) — fine for us (root, in-container),
    # but the scanner image runs as its own non-root user (uid 1000) and reads
    # this same path as a sibling container's bind mount, so it needs at least
    # read+traverse. Unlike the sandbox image (root), sonar-scanner-cli isn't.
    os.chmod(workdir, 0o755)
    try:
        for fname, content in file_contents.items():
            path = os.path.join(workdir, fname.lstrip("/"))
            os.makedirs(os.path.dirname(path) or workdir, exist_ok=True)
            with open(path, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(content)

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{workdir}:/usr/src",
            "-e", f"SONAR_HOST_URL={_scanner_host_url(server_url)}",
            "-e", f"SONAR_TOKEN={token}",
            "-e", (
                f"SONAR_SCANNER_OPTS=-Dsonar.projectKey={project_key} "
                f"-Dsonar.projectName={project_key} -Dsonar.sources=."
            ),
            _SCANNER_IMAGE,
        ]
        logger.info("running on-demand scan for %s", project_key)
        proc = subprocess.run(cmd, capture_output=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(
                f"scanner exited {proc.returncode}: {proc.stderr.decode(errors='replace')[-2000:]}"
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    _wait_for_ce(project_key, server_url, token)


def build_report(
    pr_url: str,
    component: str | None = None,
    server_url: str | None = None,
    token: str | None = None,
) -> dict:
    component = component or settings.sonar_component
    server_url = server_url or settings.sonar_url
    token = token or settings.sonar_token

    issues = fetch_sonar_issues(component, server_url, token)
    pr_files = {f.get("filename", "") for f in fetch_pr_files(pr_url)}

    rows: list[dict] = []
    in_pr = 0
    for issue in issues:
        path = (issue.get("component") or "").split(":", 1)[-1]
        touched = path in pr_files
        if touched:
            in_pr += 1
        rows.append(
            {
                "file": path,
                "line": issue.get("textRange", {}).get("startLine") if issue.get("textRange") else None,
                "severity": issue.get("severity", ""),
                "type": issue.get("type", ""),
                "rule": issue.get("rule", ""),
                "message": (issue.get("message") or "")[:300],
                "in_pr": touched,
                "suggested_tier": _SEVERITY_TIER.get(issue.get("severity", ""), 3),
            }
        )

    rows.sort(key=lambda r: (-r["in_pr"], r["severity"]))
    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "pr_url": pr_url,
        "component": component,
        "server_url": server_url,
        "total_open_issues": len(rows),
        "issues_touching_pr": in_pr,
        "summary": {
            "vulnerabilities": sum(1 for r in rows if r["type"] == "VULNERABILITY"),
            "bugs": sum(1 for r in rows if r["type"] == "BUG"),
            "code_smells": sum(1 for r in rows if r["type"] == "CODE_SMELL"),
        },
        "issues": rows,
    }


def markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# PatchCourt — SonarQube baseline",
        "",
        f"- **PR** `{report['pr_url']}`",
        f"- **Component** `{report['component']}` @ `{report['server_url']}`",
        f"- **Generated** `{report['generated_at']}`",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Open issues | {report['total_open_issues']} |",
        f"| Issues touching changed files | **{report['issues_touching_pr']}** |",
        f"| Vulnerabilities | {s['vulnerabilities']} |",
        f"| Bugs | {s['bugs']} |",
        f"| Code smells | {s['code_smells']} |",
        "",
        "> Tier mapping — BLOCKER/CRITICAL ⇒ T1 (hard tool fact), MAJOR ⇒ T2 ",
        "> (needs corroboration), MINOR ⇒ T3, INFO ⇒ T4. PatchCourt never blocks ",
        "> on T5 (LLM) evidence alone.",
        "",
        "## Issues",
        "",
    ]
    if not report["issues"]:
        lines.append("No open issues.")
        return "\n".join(lines)
    lines.append("| File | Line | Sev | Type | Rule | In PR | Suggested tier |")
    lines.append("|------|------|-----|------|------|-------|----------------|")
    for row in report["issues"]:
        lines.append(
            "| `{}` | {} | {} | {} | `{}` | {} | T{} |".format(
                row["file"],
                row["line"] if row["line"] else "—",
                row["severity"],
                row["type"],
                row["rule"],
                "**YES**" if row["in_pr"] else "",
                row["suggested_tier"],
            )
        )
    lines.append("")
    lines.append("### Top messages")
    lines.append("")
    for row in report["issues"][:10]:
        badge = "🚨" if row["in_pr"] else "·"
        lines.append(f"- {badge} `{row['file']}:{row['line'] or '?'}` **{row['severity']}** — {row['message']}")
    return "\n".join(lines)


def _reports_dir() -> "Path":
    """Stable reports dir anchored to the project root (not cwd)."""
    from pathlib import Path as _Path

    return _Path(__file__).resolve().parents[2] / "reports"


def write_report(pr_url: str, report: dict) -> tuple[str, str]:
    from pathlib import Path

    owner, repo, num = parse_pr_url(pr_url)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = _reports_dir()
    out_dir.mkdir(exist_ok=True)
    base = out_dir / f"baseline-{owner}-{repo}-{num}-{ts}"
    md_path = f"{base}.md"
    json_path = f"{base}.json"
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(markdown(report))
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    return md_path, json_path


def latest_report() -> dict | None:
    """The most recently written baseline report (dict from JSON), or None."""
    pattern = re.compile(r"^baseline-.*\.json$")
    candidates = [p for p in _reports_dir().glob("baseline-*.json") if pattern.match(p.name)]
    if not candidates:
        return None
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    with open(newest, encoding="utf-8") as fh:
        return json.load(fh)


def compare_with_review(report: dict, claims: list[dict], verdict: str, overall_score: float) -> dict:
    """Reconcile SonarQube issues (in the PR) with PatchCourt claims.

    Groups:
    - confirmed/kept  — Sonar issue backed by a corroborated/tool PatchCourt claim
      on the same file:line.
    - down-tiered     — Sonar issue with no PatchCourt support on that line
      (likely false positive → unbacked, N−M).
    - sonar_missed    — strong PatchCourt tool claims SonarQube never reported.
    """
    by_line: dict[tuple, list[dict]] = {}
    for c in claims:
        line = int(c.get("line") or 0)
        key = (c.get("file", ""), line)
        by_line.setdefault(key, []).append(c)

    confirmed: list[dict] = []
    down_tiered: list[dict] = []
    sonar_keys: set[tuple] = set()
    for issue in report.get("issues", []):
        if not issue.get("in_pr"):
            continue
        line = int(issue.get("line") or 0)
        key = (issue.get("file", ""), line)
        sonar_keys.add(key)
        backed = any(
            c.get("source") == "tool" or c.get("corroborated") or (c.get("tier") or 5) <= 2
            for c in by_line.get(key, [])
        )
        (confirmed if backed else down_tiered).append(issue)

    sonar_missed: list[dict] = []
    for c in claims:
        if int(c.get("line") or 0) == 0:
            continue
        if not (c.get("source") == "tool" or c.get("corroborated")):
            continue
        if (int(c.get("severity") or 0) < 3 and not c.get("corroborated")):
            continue
        key = (c.get("file", ""), int(c.get("line") or 0))
        if key in sonar_keys:
            continue
        sonar_missed.append(
            {
                "file": c.get("file"),
                "line": c.get("line"),
                "severity": c.get("severity"),
                "agent": c.get("agent"),
                "tier": c.get("tier"),
                "issue": (c.get("issue") or "")[:160],
            }
        )

    n = len(confirmed) + len(down_tiered)
    return {
        "verdict": verdict,
        "overall_score": overall_score,
        "counts": {
            "raw": n,
            "confirmed": len(confirmed),
            "suppressed": len(down_tiered),
            "sonar_missed": len(sonar_missed),
        },
        "confirmed": confirmed,
        "down_tiered": down_tiered,
        "sonar_missed": sonar_missed,
    }