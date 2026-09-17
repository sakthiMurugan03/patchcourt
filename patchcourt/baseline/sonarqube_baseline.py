"""SonarQube baseline — pull unresolved quality issues from a SonarQube server
and compare them against the files touched by a GitHub PR. Produces a markdown
report (and raw JSON) that maps SonarQube findings to PatchCourt evidence tiers."""

from __future__ import annotations

import datetime as _dt
import json
import re

import httpx

from patchcourt.config import settings

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
        "generated_at": _dt.datetime.utcnow().isoformat() + "Z",
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


def write_report(pr_url: str, report: dict) -> tuple[str, str]:
    import os
    from pathlib import Path

    owner, repo, num = parse_pr_url(pr_url)
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path.cwd() / "reports"
    out_dir.mkdir(exist_ok=True)
    base = out_dir / f"baseline-{owner}-{repo}-{num}-{ts}"
    md_path = f"{base}.md"
    json_path = f"{base}.json"
    with open(md_path, "w") as fh:
        fh.write(markdown(report))
    with open(json_path, "w") as fh:
        json.dump(report, fh, indent=2)
    return md_path, json_path