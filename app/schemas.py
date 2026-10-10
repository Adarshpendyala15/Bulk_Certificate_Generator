from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecipientInput(BaseModel):
    name: str
    email: str
    course_or_role: str | None = None


class JobCreateRequest(BaseModel):
    event_name: str = Field(..., min_length=1)
    issuer_name: str = Field(..., min_length=1)
    issue_date: date | None = None
    recipients: list[RecipientInput]

    model_config = ConfigDict(populate_by_name=True)


class CertificateSummary(BaseModel):
    id: str
    recipient_name: str
    recipient_email: str
    status: str
    error_message: str | None = None
    download_url: str | None = None
    file_path: str | None = None

    model_config = ConfigDict(from_attributes=True)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    total_count: int
    succeeded_count: int
    failed_count: int
    pending_count: int


class PaginationInfo(BaseModel):
    limit: int
    offset: int
    total: int


class JobDetailResponse(BaseModel):
    job_id: str
    event_name: str
    issuer_name: str
    issue_date: date
    status: str
    total_count: int
    succeeded_count: int
    failed_count: int
    pending_count: int
    progress_percentage: float
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    certificates: list[CertificateSummary]
    pagination: PaginationInfo


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str


class DownloadResponse(BaseModel):
    message: str
    file_path: str | None = None


class ZipResponse(BaseModel):
    message: str
    job_id: str
    file_count: int


__all__ = [
    "RecipientInput",
    "JobCreateRequest",
    "CertificateSummary",
    "JobCreateResponse",
    "JobDetailResponse",
    "HealthResponse",
    "ErrorResponse",
    "PaginationInfo",
    "DownloadResponse",
    "ZipResponse",
]
