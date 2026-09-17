"""Audit-trail ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PRReview(Base):
    __tablename__ = "pr_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pr_url: Mapped[str] = mapped_column(String(512))
    owner: Mapped[str] = mapped_column(String(128), default="")
    repo: Mapped[str] = mapped_column(String(128), default="")
    pr_number: Mapped[int] = mapped_column(Integer, default=0)
    verdict: Mapped[str] = mapped_column(String(32))
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    raw_report: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    claims: Mapped[list["ClaimRecord"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    debates: Mapped[list["DebateRecord"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ClaimRecord(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("pr_reviews.id"))
    agent: Mapped[str] = mapped_column(String(64))
    issue: Mapped[str] = mapped_column(Text)
    file: Mapped[str] = mapped_column(String(512))
    line: Mapped[int] = mapped_column(Integer, default=0)
    severity: Mapped[int] = mapped_column(Integer)
    tier: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    corroborated: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="llm")

    review: Mapped["PRReview"] = relationship(back_populates="claims")
    evidence: Mapped[list["EvidenceRecord"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"))
    tier: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    claim: Mapped["ClaimRecord"] = relationship(back_populates="evidence")


class DebateRecord(Base):
    __tablename__ = "debates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("pr_reviews.id"))
    file: Mapped[str] = mapped_column(String(512))
    issue: Mapped[str] = mapped_column(Text)
    supporting: Mapped[str] = mapped_column(Text, default="")
    opposing: Mapped[str] = mapped_column(Text, default="")
    rounds: Mapped[int] = mapped_column(Integer, default=0)

    review: Mapped["PRReview"] = relationship(back_populates="debates")