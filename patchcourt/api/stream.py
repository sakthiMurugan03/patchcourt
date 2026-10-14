"""Server-Sent Events (SSE) streaming for live review / debate output.

``GET /api/review/{pr_id}/stream`` runs the adjudication pipeline and pushes
events to the browser as they become available. The heavy review itself is a
single coroutine (``run_review``), so while it runs the stream emits periodic
keep-alive comments and then flushes the debate transcripts and verdict.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from patchcourt.ingest import parse_pr_url

logger = logging.getLogger("patchcourt.api.stream")
router = APIRouter(prefix="/api/review", tags=["stream"])

# Emit a comment every N seconds so proxies/browsers don't drop the connection.
HEARTBEAT_SECONDS = 15.0


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def sse_event(data: Any, event: str | None = None) -> str:
    """Format a single SSE frame (``event:`` line optional)."""
    body = json.dumps(_jsonable(data), default=str)
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {body}\n\n"


def resolve_pr_url(pr_id: str, repo: str | None, pr_url: str | None) -> str:
    """Resolve the requested PR to a GitHub PR URL.

    Accepts either a full URL as ``pr_id``, or a PR number together with a
    ``repo`` (``owner/name``) query parameter.
    """
    if pr_url:
        candidate = pr_url
    elif "github.com" in pr_id:
        candidate = pr_id
    elif repo:
        candidate = f"https://github.com/{repo}/pull/{pr_id}"
    else:
        candidate = pr_id

    try:
        parse_pr_url(candidate)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "category": "pr_not_found",
                "message": "Provide a GitHub PR URL or a PR number plus a `repo` query parameter",
            },
        ) from exc
    return candidate


async def _review_event_stream(pr_url: str) -> AsyncIterator[str]:
    """Yield SSE frames for a review run."""
    yield sse_event({"stage": "started", "pr_url": pr_url}, "status")

    from patchcourt.graph import run_review

    task = asyncio.create_task(run_review(pr_url))
    try:
        while True:
            done, _pending = await asyncio.wait({task}, timeout=HEARTBEAT_SECONDS)
            if done:
                break
            yield ": keep-alive\n\n"
        report = task.result()
    except asyncio.CancelledError:
        task.cancel()
        raise
    except Exception as exc:  # noqa: BLE001 - surface a clean SSE error frame
        logger.exception("Streaming review failed for %s", pr_url)
        try:
            from patchcourt.api.app import friendly_error

            category, message = friendly_error(exc)
        except Exception:  # pragma: no cover - defensive
            category, message = "unknown", "Review failed"
        yield sse_event({"stage": "error", "category": category, "message": message}, "error")
        return

    for index, debate in enumerate(getattr(report, "debate_transcripts", []) or []):
        yield sse_event({"index": index, "debate": _jsonable(debate)}, "debate")

    yield sse_event(
        {
            "pr_url": getattr(report, "pr_url", pr_url),
            "verdict": report.verdict,
            "overall_score": report.overall_score,
            "contextual_summary": report.contextual_summary,
            "debate_count": len(getattr(report, "debate_transcripts", []) or []),
        },
        "verdict",
    )
    yield sse_event({"stage": "done"}, "done")


@router.get("/{pr_id}/stream")
async def stream_review(
    pr_id: str,
    repo: str | None = Query(default=None, description="owner/name, when pr_id is a number"),
    pr_url: str | None = Query(default=None, description="Full PR URL (overrides pr_id)"),
) -> StreamingResponse:
    """Stream review/debate output as Server-Sent Events."""
    resolved = resolve_pr_url(pr_id, repo, pr_url)
    return StreamingResponse(
        _review_event_stream(resolved),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
