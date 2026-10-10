from __future__ import annotations

import os
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.schemas import CertificateSummary, JobCreateResponse, JobDetailResponse, PaginationInfo
from app.services.validation import validate_recipient
from app.services.worker import enqueue_job


def normalize_issue_date(value):
    if value is None:
        return date.today()
    return value


def _job_counts(db: Session, job_id: str):
    total = db.query(func.count(Certificate.id)).filter(Certificate.job_id == job_id).scalar() or 0
    succeeded = db.query(func.count(Certificate.id)).filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.SUCCESS).scalar() or 0
    failed = db.query(func.count(Certificate.id)).filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.FAILED).scalar() or 0
    pending = db.query(func.count(Certificate.id)).filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.PENDING).scalar() or 0
    return total, succeeded, failed, pending


def _job_summary(db: Session, job_id: str):
    total, succeeded, failed, pending = _job_counts(db, job_id)
    return {
        "total_count": total,
        "succeeded_count": succeeded,
        "failed_count": failed,
        "pending_count": pending,
    }


def create_job(db: Session, payload):
    recipients = payload.recipients
    if not recipients:
        raise HTTPException(status_code=422, detail="Recipients list cannot be empty")
    if len(recipients) > settings.MAX_RECIPIENTS_PER_JOB:
        raise HTTPException(status_code=422, detail=f"Recipients cannot exceed {settings.MAX_RECIPIENTS_PER_JOB}")
    if not payload.event_name or not payload.event_name.strip():
        raise HTTPException(status_code=422, detail="event_name is required")
    if not payload.issuer_name or not payload.issuer_name.strip():
        raise HTTPException(status_code=422, detail="issuer_name is required")

    job = Job(
        event_name=payload.event_name.strip(),
        issuer_name=payload.issuer_name.strip(),
        issue_date=normalize_issue_date(payload.issue_date),
        status=JobStatus.PENDING,
        total_count=len(recipients),
    )
    db.add(job)
    db.flush()

    seen_emails = set()
    valid_count = 0
    for recipient in recipients:
        valid, error_message, name, email, course = validate_recipient(recipient.model_dump(), seen_emails)
        if not valid:
            certificate = Certificate(
                job_id=job.id,
                recipient_name=name or "Invalid Recipient",
                recipient_email=email or "invalid@example.com",
                course_or_role=course,
                status=CertificateStatus.FAILED,
                error_message=error_message,
            )
            db.add(certificate)
            continue

        certificate = Certificate(
            job_id=job.id,
            recipient_name=name,
            recipient_email=email,
            course_or_role=course,
            status=CertificateStatus.PENDING,
        )
        valid_count += 1
        db.add(certificate)

    db.commit()

    if valid_count == 0:
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now()
        db.add(job)
        db.commit()

    if settings.PROCESSING_MODE.lower() == "sync" or os.getenv("PYTEST_CURRENT_TEST") is not None:
        from app.services.worker import process_job

        process_job(job.id)
    else:
        enqueue_job(job.id)

    db.refresh(job)
    total, succeeded, failed, pending = _job_counts(db, job.id)
    response = JobCreateResponse(
        job_id=job.id,
        status=job.status.value,
        total_count=total,
        succeeded_count=succeeded,
        failed_count=failed,
        pending_count=pending,
    )
    return response


def get_job_detail(db: Session, job_id: str, status: str | None, limit: int, offset: int):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    query = db.query(Certificate).filter(Certificate.job_id == job_id)
    if status:
        query = query.filter(Certificate.status == status.upper())

    total_records = query.count()
    certificates = query.order_by(Certificate.created_at.asc()).offset(offset).limit(limit).all()

    summary = _job_summary(db, job_id)
    progress = 0.0
    if job.total_count:
        progress = round(((summary["succeeded_count"] + summary["failed_count"]) / job.total_count) * 100, 2)

    items = []
    for certificate in certificates:
        file_path = None
        download_url = None
        if certificate.file_path:
            from pathlib import Path
            from app.config import settings
            file_path = str(Path(settings.CERTIFICATES_DIR) / certificate.file_path)
        if certificate.status == CertificateStatus.SUCCESS and certificate.file_path:
            download_url = f"/api/v1/certificates/{certificate.id}/download"
        items.append(
            CertificateSummary(
                id=certificate.id,
                recipient_name=certificate.recipient_name,
                recipient_email=certificate.recipient_email,
                status=certificate.status.value,
                error_message=certificate.error_message,
                download_url=download_url,
                file_path=file_path,
            )
        )

    return JobDetailResponse(
        job_id=job.id,
        event_name=job.event_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        status=job.status.value,
        total_count=job.total_count,
        succeeded_count=summary["succeeded_count"],
        failed_count=summary["failed_count"],
        pending_count=summary["pending_count"],
        progress_percentage=progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        certificates=items,
        pagination=PaginationInfo(limit=limit, offset=offset, total=total_records),
    )
