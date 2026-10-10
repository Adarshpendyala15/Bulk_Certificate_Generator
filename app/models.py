from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class CertificateStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.PENDING, nullable=False, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    certificates: Mapped[list["Certificate"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    course_or_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[CertificateStatus] = mapped_column(default=CertificateStatus.PENDING, nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped[Job] = relationship(back_populates="certificates")


__all__ = ["Job", "Certificate", "JobStatus", "CertificateStatus"]
