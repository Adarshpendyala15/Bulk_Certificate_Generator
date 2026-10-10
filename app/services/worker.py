from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.services import certificate_generator


def utcnow():
    return datetime.now(timezone.utc)


def _counts_for_job(db: Session, job_id: str):
    certificates = db.query(Certificate).filter(Certificate.job_id == job_id).all()
    succeeded = sum(1 for item in certificates if item.status == CertificateStatus.SUCCESS)
    failed = sum(1 for item in certificates if item.status == CertificateStatus.FAILED)
    pending = sum(1 for item in certificates if item.status == CertificateStatus.PENDING)
    total = len(certificates)
    return total, succeeded, failed, pending


def _finalize_job_status(db: Session, job_id: str):
    job = db.get(Job, job_id)
    if job is None:
        return
    total, succeeded, failed, pending = _counts_for_job(db, job_id)

    if total == 0:
        job.status = JobStatus.FAILED
    elif succeeded == total:
        job.status = JobStatus.COMPLETED
    elif failed == total:
        job.status = JobStatus.FAILED
    elif failed > 0 and succeeded > 0:
        job.status = JobStatus.COMPLETED_WITH_ERRORS
    elif pending > 0:
        job.status = JobStatus.PENDING
    else:
        job.status = JobStatus.PROCESSING

    if job.status in {JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS, JobStatus.FAILED}:
        job.completed_at = utcnow()
    db.commit()


def process_job(job_id: str):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return

        job.status = JobStatus.PROCESSING
        job.started_at = job.started_at or utcnow()
        db.commit()

        certificates = db.query(Certificate).filter(Certificate.job_id == job_id).order_by(Certificate.created_at.asc()).all()
        for certificate in certificates:
            if certificate.status in {CertificateStatus.SUCCESS, CertificateStatus.FAILED}:
                continue
            certificate.status = CertificateStatus.PROCESSING
            db.add(certificate)
            db.commit()

            try:
                relative_path = certificate_generator.generate_certificate_pdf(
                    job_id=job.id,
                    cert_id=certificate.id,
                    name=certificate.recipient_name,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    course_or_role=certificate.course_or_role,
                )
                certificate.file_path = relative_path
                certificate.status = CertificateStatus.SUCCESS
                certificate.error_message = None
                certificate.completed_at = utcnow()
            except Exception as exc:
                certificate.status = CertificateStatus.FAILED
                certificate.error_message = str(exc)[:500]
                certificate.completed_at = utcnow()

            db.add(certificate)
            db.commit()

        _finalize_job_status(db, job_id)
    finally:
        db.close()


def enqueue_job(job_id: str):
    if settings.PROCESSING_MODE.lower() == "sync":
        process_job(job_id)
        return

    from app.main import app

    if hasattr(app.state, "executor"):
        app.state.executor.submit(process_job, job_id)
