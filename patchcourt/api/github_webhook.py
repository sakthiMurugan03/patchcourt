"""Real-world GitHub webhook integration.

``POST /api/webhooks/github`` receives GitHub ``pull_request`` events, verifies
the ``x-hub-signature-256`` HMAC-SHA256 signature, runs PatchCourt's review
adjudication, and posts the plain-English verdict back to the PR as a comment
using ``httpx``.

Reviewing a PR can take far longer than GitHub's webhook timeout, so the work
is dispatched to a Starlette background task and the request is acknowledged
immediately.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from patchcourt.config import settings
from patchcourt.ingest import parse_pr_url

logger = logging.getLogger("patchcourt.api.github_webhook")
router = APIRouter(prefix="/api/webhooks", tags=["github"])

GITHUB_API_BASE = "https://api.github.com"
_SIGNATURE_HEADER = "x-hub-signature-256"
_REVIEW_ACTIONS = {"opened", "synchronize"}

_VERDICT_EMOJI = {"MERGE": "✅", "NEEDS_REVIEW": "⚠️", "BLOCK": "⛔"}
_VERDICT_BLURB = {
    "MERGE": "No material risk found — this pull request looks safe to merge.",
    "NEEDS_REVIEW": "PatchCourt found low-confidence concerns that warrant a human look before merging.",
    "BLOCK": "PatchCourt found evidence-backed issues that should be fixed before merging.",
}


def verify_signature(
    raw_body: bytes,
    signature_header: str | None,
    secret: str | None = None,
) -> bool:
    """Validate a GitHub ``x-hub-signature-256`` header against ``raw_body``."""
    effective_secret = secret if secret is not None else settings.github_webhook_secret
    if not effective_secret or not signature_header:
        return False

    scheme, _, received = signature_header.partition("=")
    if scheme != "sha256" or not received:
        return False

    expected = hmac.new(
        effective_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, received)


def _git_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "patchcourt",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def build_verdict_comment(report: Any) -> str:
    """Render a plain-English verdict summary suitable for a PR comment."""
    verdict = getattr(report, "verdict", "NEEDS_REVIEW")
    score = getattr(report, "overall_score", 0.0)
    summary = getattr(report, "contextual_summary", {}) or {}
    assessments = getattr(report, "finding_assessments", []) or []

    emoji = _VERDICT_EMOJI.get(verdict, "⚖️")
    blurb = _VERDICT_BLURB.get(verdict, "PatchCourt completed its review.")

    total = summary.get("total", len(assessments))
    by_action: dict[str, int] = summary.get("by_action", {}) or {}
    blocking = summary.get("blocking", 0)

    lines: list[str] = [
        f"## {emoji} PatchCourt verdict: **{verdict}**",
        "",
        f"**Risk score:** {score:.1f} (higher = riskier)",
        "",
        blurb,
        "",
    ]

    if total:
        lines.append(
            f"PatchCourt adjudicated **{total}** finding(s); "
            f"**{blocking}** flagged as blocking."
        )
        lines.append("")

    blocking_findings = [
        a for a in assessments if getattr(a, "contextual_action", "") == "block"
    ]
    if blocking_findings:
        lines.append("### ⛔ Blocking findings")
        for a in blocking_findings[:10]:
            file = str(getattr(a, "file", "") or "").replace("`", "'")
            line = getattr(a, "line", 0)
            message = str(getattr(a, "message", "") or "").replace("`", "'")
            category = str(getattr(a, "category", "issue") or "issue").upper()
            lines.append(f"- `{file}:{line}` — **[{category}]** {message}")
        lines.append("")

    ordered = [
        action
        for action in ("block", "remediate", "review", "human_review", "acknowledge")
        if by_action.get(action)
    ]
    if ordered:
        lines.append("### Recommended actions")
        for action in ordered:
            lines.append(f"- **{action.replace('_', ' ')}** — {by_action[action]} finding(s)")
        lines.append("")

    lines.append(
        "_Automated review by PatchCourt — multi-agent courtroom debate with "
        "evidence-tiered adjudication._"
    )
    return "\n".join(lines)


async def post_pr_comment(
    pr_url: str,
    body: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Post ``body`` as a comment on the pull request at ``pr_url``."""
    owner, repo, number = parse_pr_url(pr_url)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{number}/comments"

    if client is not None:
        response = await client.post(url, json={"body": body}, headers=_git_headers())
        response.raise_for_status()
        return response.json() if response.content else {}

    async with httpx.AsyncClient(headers=_git_headers(), timeout=30) as http:
        response = await http.post(url, json={"body": body})
        response.raise_for_status()
        return response.json() if response.content else {}


async def process_pull_request_event(pr_url: str) -> dict[str, Any]:
    """Run adjudication for a PR and post the verdict comment back to GitHub."""
    from patchcourt.graph import run_review

    try:
        report = await run_review(pr_url)
    except Exception:  # noqa: BLE001 - background work must never crash the loop
        logger.exception("Webhook review failed for %s", pr_url)
        return {"ok": False, "stage": "review", "pr_url": pr_url}

    comment = build_verdict_comment(report)
    try:
        await post_pr_comment(pr_url, comment)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to post verdict comment for %s", pr_url)
        return {"ok": False, "stage": "comment", "pr_url": pr_url}

    return {
        "ok": True,
        "pr_url": pr_url,
        "verdict": getattr(report, "verdict", None),
        "overall_score": getattr(report, "overall_score", None),
    }


@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Handle GitHub webhook deliveries."""
    secret = settings.github_webhook_secret
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_WEBHOOK_SECRET not configured — cannot verify signatures",
        )

    raw_body = await request.body()
    if not verify_signature(raw_body, request.headers.get(_SIGNATURE_HEADER), secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = request.headers.get("x-github-event", "")
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if event == "ping":
        return {"ok": True, "event": "ping"}

    if event != "pull_request":
        return {"accepted": False, "reason": f"unhandled event {event}"}

    action = payload.get("action", "")
    if action not in _REVIEW_ACTIONS:
        return {"accepted": False, "reason": f"unhandled action {action}"}

    pr_url = (payload.get("pull_request") or {}).get("html_url")
    if not pr_url:
        raise HTTPException(status_code=400, detail="payload missing pull_request.html_url")

    background_tasks.add_task(process_pull_request_event, pr_url)
    logger.info("accepted pull_request %s for %s", action, pr_url)
    return {"accepted": True, "action": action, "pr_url": pr_url}
