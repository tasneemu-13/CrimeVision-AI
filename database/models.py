"""
SQLAlchemy ORM models for CrimeVision AI.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from database.connection import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    badge_number = Column(String(100), nullable=True)
    department = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    cases = relationship("Case", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    token = Column(String(128), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(64), primary_key=True)  # Format: CV-YYYYMMDD-XXXX
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    incident_type = Column(String(64), nullable=False, default="Burglary")  # Homicide, Burglary, Assault, Vandalism, etc.
    status = Column(String(32), nullable=False, default="Open")            # Open, In Progress, Under Review, Closed
    location = Column(String(255), nullable=True)
    incident_date = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="cases")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    custody_events = relationship("CustodyEvent", back_populates="case", cascade="all, delete-orphan")
    ledger_events = relationship("LedgerEvent", back_populates="case", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="case", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="case", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(64), primary_key=True)  # Format: IMG-001, AUD-001, VID-001
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(32), nullable=False)  # IMAGE, AUDIO, VIDEO, DOCUMENT
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    mime_type = Column(String(128), nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)
    notes = Column(Text, nullable=True)

    case = relationship("Case", back_populates="evidence")
    analysis_results = relationship("AnalysisResult", back_populates="evidence", cascade="all, delete-orphan")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    evidence_id = Column(String(64), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    analysis_type = Column(String(64), nullable=False)  # IMAGE_DETECTION, AUDIO_TRANSCRIPT, VIDEO_TRACKING
    engine_used = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="completed")  # completed, failed, pending
    result_json = Column(Text, nullable=False)  # Serialized JSON analysis output
    created_at = Column(DateTime, default=utc_now, nullable=False)

    evidence = relationship("Evidence", back_populates="analysis_results")


class LedgerEvent(Base):
    __tablename__ = "ledger_events"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    evidence_id = Column(String(64), nullable=False, index=True)
    source = Column(String(32), nullable=False)  # IMAGE, AUDIO, VIDEO
    t_offset = Column(Float, nullable=False, default=0.0)
    description = Column(Text, nullable=False)
    legal_category = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    case = relationship("Case", back_populates="ledger_events")


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    evidence_id = Column(String(64), nullable=False)
    action = Column(String(255), nullable=False)
    investigator_name = Column(String(255), nullable=False)
    badge_number = Column(String(100), nullable=True)
    sha256_digest = Column(String(64), nullable=True)
    timestamp_utc = Column(DateTime, default=utc_now, nullable=False)

    case = relationship("Case", back_populates="custody_events")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    signoff_investigator = Column(String(255), nullable=True)
    signoff_badge = Column(String(100), nullable=True)
    generated_at = Column(DateTime, default=utc_now, nullable=False)

    case = relationship("Case", back_populates="reports")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(64), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    timestamp_utc = Column(DateTime, default=utc_now, nullable=False)

    case = relationship("Case", back_populates="chat_messages")
