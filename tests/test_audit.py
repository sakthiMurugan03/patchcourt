"""Audit-trail persistence to SQLAlchemy (SQLite in-memory)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from patchcourt.agents.schemas import Claim, Evidence, ReviewReport
from patchcourt.db.audit import store_audit
from patchcourt.db.models import PRReview, ClaimRecord, EvidenceRecord, DebateRecord, Base


def _report() -> ReviewReport:
    return ReviewReport(
        pr_url="https://github.com/a/b/pull/9",
        overall_score=12.3,
        verdict="BLOCK",
        claims=[
            Claim(
                agent="tools",
                issue="SQL injection",
                file="a.py",
                line=4,
                severity=5,
                evidence=[Evidence(tier=1, text="[semgrep] raw concat"), Evidence(tier=2, text="[bandit] same line")],
                confidence=1.0,
                tier=1,
                corroborated=True,
                source="tool",
            ),
            Claim(
                agent="quality",
                issue="UNUSED_VAR",
                file="b.py",
                line=2,
                severity=2,
                evidence=[Evidence(tier=5, text="llm guess")],
                confidence=0.3,
                tier=5,
            ),
        ],
        debate_transcripts=[
            {
                "file": "a.py",
                "issue": "SQL injection",
                "supporting": "tool backs it",
                "opposing": "false positive",
                "rounds": 2,
            }
        ],
    )


def test_store_audit_roundtrip():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        rid = store_audit(_report(), session=s)

    with Session() as s:
        review = s.get(PRReview, rid)
        assert review.pr_url == "https://github.com/a/b/pull/9"
        assert review.verdict == "BLOCK"
        assert review.overall_score == 12.3

        claims = s.query(ClaimRecord).filter_by(review_id=rid).all()
        assert len(claims) == 2
        tool = next(c for c in claims if c.source == "tool")
        assert tool.corroborated is True
        assert tool.tier == 1
        assert len(tool.evidence) == 2
        assert tool.evidence[0].tier == 1

        debates = s.query(DebateRecord).filter_by(review_id=rid).all()
        assert len(debates) == 1
        assert debates[0].rounds == 2
        assert debates[0].file == "a.py"


def test_store_audit_t5_claim_recorded_with_evidence():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as s:
        rid = store_audit(_report(), session=s)

    with Session() as s:
        claims = s.query(ClaimRecord).filter_by(review_id=rid).all()
        t5 = next(c for c in claims if c.tier == 5)
        assert t5.corroborated is False
        assert len(t5.evidence) == 1