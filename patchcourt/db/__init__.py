"""Database layer — PostgreSQL/SQLite audit trail (SQLAlchemy)."""
from __future__ import annotations

from patchcourt.db.models import Base, ClaimRecord, DebateRecord, EvidenceRecord, PRReview
from patchcourt.db.session import get_engine, init_db, session_scope
from patchcourt.db.audit import store_audit

__all__ = [
    "Base",
    "ClaimRecord",
    "DebateRecord",
    "EvidenceRecord",
    "PRReview",
    "get_engine",
    "init_db",
    "session_scope",
    "store_audit",
]