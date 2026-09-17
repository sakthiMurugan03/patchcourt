"""GitHub webhook — enqueues a review task when a PR opens/synchronizes."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from patchcourt.config import settings

logger = logging.getLogger("patchcourt.api.webhook")
router = APIRouter(prefix="/api/webhook", tags=["webhook"])

_REVIEW_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}


@router.post("/github")
async def github_webhook(request: Request) -> dict[str, Any]:
    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event == "ping":
        return {"ok": True, "event": "ping"}

    if event != "pull_request":
        return {"accepted": False, "reason": f"unhandled event {event}"}

    action = payload.get("action", "")
    if action not in _REVIEW_ACTIONS:
        return {"accepted": False, "reason": f"unhandled action {action}"}

    if not settings.redis_url:
        raise HTTPException(
            status_code=503, detail="REDIS_URL not configured — async processing disabled"
        )

    from patchcourt.worker import review_pr_task

    pr_url = payload["pull_request"]["html_url"]
    task = review_pr_task.delay(pr_url)
    logger.info("enqueued review for %s (task %s)", pr_url, task.id)
    return {"accepted": True, "task_id": str(task.id), "pr_url": pr_url}