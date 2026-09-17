"""GitHub PR ingestion via httpx."""
from __future__ import annotations

import re

import httpx

from patchcourt.agents.schemas import PRContext
from patchcourt.config import settings


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract owner, repo, pr_number from a GitHub PR URL."""
    m = re.search(
        r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<num>\d+)",
        url.strip().rstrip("/"),
    )
    if not m:
        raise ValueError(f"Not a valid GitHub PR URL: {url}")
    return m.group("owner"), m.group("repo"), int(m.group("num"))


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


async def _fetch_raw(client, base: str, path: str, ref: str | None) -> str | None:
    """Fetch the raw file content so analysis tools see clean source, not patch text."""
    url = f"{base}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    try:
        resp = await client.get(url, headers={**_headers(), "Accept": "application/vnd.github.raw"})
        if resp.is_success:
            return resp.text
    except httpx.HTTPError:
        pass
    return None


async def fetch_pr(url_or_id: str | tuple[str, str, int]) -> PRContext:
    if isinstance(url_or_id, str):
        owner, repo, num = parse_pr_url(url_or_id)
    else:
        owner, repo, num = url_or_id
    base = f"https://api.github.com/repos/{owner}/{repo}"

    async with httpx.AsyncClient(headers=_headers(), timeout=30) as client:
        pr_resp = await client.get(f"{base}/pulls/{num}")
        pr_resp.raise_for_status()
        pr_data = pr_resp.json()

        files_resp = await client.get(f"{base}/pulls/{num}/files")
        files_resp.raise_for_status()
        files = files_resp.json()

        diff_resp = await client.get(f"{base}/pulls/{num}", headers={**_headers(), "Accept": "application/vnd.github.v3.diff"})
        diff_resp.raise_for_status()
        diff = diff_resp.text

        file_contents: dict[str, str] = {}
        patches: dict[str, str] = {}
        head_sha = (pr_data.get("head") or {}).get("sha")
        for f in files:
            fname = f.get("filename", "")
            if f.get("patch"):
                patches[fname] = f["patch"]
            raw = await _fetch_raw(client, base, fname, head_sha)
            if raw is not None:
                file_contents[fname] = raw

    ctx = PRContext(
        owner=owner,
        repo=repo,
        pr_number=num,
        title=pr_data.get("title", ""),
        body=pr_data.get("body", ""),
        diff=diff,
        changed_files=files,
        file_contents=file_contents,
    )
    ctx.patches = patches
    ctx.rag_query = f"PR #{num}: {ctx.title}\n\n{ctx.body}\n\nChanged files: {', '.join(file_contents.keys())}"
    return ctx
