"""Async worker — Celery tasks that run the review pipeline and persist the audit trail."""
from __future__ import annotations

import asyncio
import logging

from celery import Celery

from patchcourt.config import settings

logger = logging.getLogger("patchcourt.worker")

celery_app = Celery(
    "patchcourt",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0",
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(bind=True, name="patchcourt.review_pr", max_retries=1)
def review_pr_task(self, pr_url: str) -> dict:
    """Run the full review for a PR and store the audit record."""
    from patchcourt.db import store_audit
    from patchcourt.graph import run_review

    logger.info("review task started for %s", pr_url)
    try:
        report = asyncio.run(run_review(pr_url))
    except Exception as exc:  # transient failures (GitHub limits) retry once
        logger.warning("review failed for %s: %s", pr_url, exc)
        raise self.retry(exc=exc, countdown=15)
    review_id = None
    if settings.database_url:
        try:
            review_id = store_audit(report)
        except Exception:
            logger.exception("could not persist audit record for %s", pr_url)
    return {
        "pr_url": report.pr_url,
        "verdict": report.verdict,
        "overall_score": report.overall_score,
        "audit_id": review_id,
    }