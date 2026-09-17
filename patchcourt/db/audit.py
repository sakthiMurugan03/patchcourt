"""Persist a review + full audit trail (claims, evidence tiers, debates, verdict)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session as SASession

from patchcourt.agents.schemas import Claim, ReviewReport
from patchcourt.db.models import ClaimRecord, DebateRecord, EvidenceRecord, PRReview


def _claim_rows(review_id: int, claims: list[Claim]) -> list[ClaimRecord]:
    rows: list[ClaimRecord] = []
    for c in claims:
        cr = ClaimRecord(
            review_id=review_id,
            agent=c.agent,
            issue=c.issue,
            file=c.file,
            line=c.line,
            severity=c.severity,
            tier=c.tier,
            confidence=c.confidence,
            corroborated=c.corroborated,
            source=c.source,
        )
        cr.evidence = [
            EvidenceRecord(tier=e.tier, text=e.text) for e in c.evidence
        ]
        rows.append(cr)
    return rows


def _debate_rows(review_id: int, debate_transcripts: list[dict]) -> list[DebateRecord]:
    return [
        DebateRecord(
            review_id=review_id,
            file=d.get("file", ""),
            issue=d.get("issue", ""),
            supporting=d.get("supporting", ""),
            opposing=d.get("opposing", ""),
            rounds=int(d.get("rounds", 0)),
        )
        for d in debate_transcripts
    ]


def store_audit(report: ReviewReport, session: SASession | None = None) -> int:
    """Write a review into the audit DB. ``session`` may be injected for tests."""
    if session is None:
        from patchcourt.db.session import session_scope

        with session_scope() as s:
            return _insert(s, report)
    return _insert(session, report)


def _insert(session: SASession, report: ReviewReport) -> int:
    review = PRReview(
        pr_url=report.pr_url,
        verdict=report.verdict,
        overall_score=report.overall_score,
        raw_report=json.dumps(report.model_dump()),
    )
    session.add(review)
    session.flush()

    session.add_all(_claim_rows(review.id, report.claims))
    session.add_all(_debate_rows(review.id, report.debate_transcripts))
    session.commit()
    return review.id