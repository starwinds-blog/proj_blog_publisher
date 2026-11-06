import datetime as dt
from zoneinfo import ZoneInfo
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.backend.db.database import Base

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> dt.datetime:
    return dt.datetime.now(KST)


class StoryAuditLog(Base):
    """Audit trail of story edits, validations, approvals, and publish runs."""

    __tablename__ = "story_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), index=True, nullable=False)
    action = Column(String(64), nullable=False)  # create_raw, generate_draft, validate, approve, stage, publish
    status = Column(String(32), nullable=False)  # success, failed, dry_run
    summary = Column(Text, nullable=False, default="")
    details_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), default=now_kst, nullable=False)
