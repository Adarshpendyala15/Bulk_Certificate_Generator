from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Certificate, CertificateStatus, Job

router = APIRouter(prefix="/api/v1", tags=["certificates"])


@router.get("/certificates/{certificate_id}/download")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if certificate.status != CertificateStatus.SUCCESS:
        raise HTTPException(status_code=409, detail="Certificate is not yet generated or has failed")
    if not certificate.file_path:
        raise HTTPException(status_code=409, detail="Certificate is not yet generated or has failed")

    file_path = Path(settings.CERTIFICATES_DIR) / certificate.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found")

    return FileResponse(str(file_path), media_type="application/pdf", filename=f"{certificate_id}.pdf")


@router.get("/jobs/{job_id}/download")
def download_job_zip(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    certificates = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id, Certificate.status == CertificateStatus.SUCCESS)
        .order_by(Certificate.created_at.asc())
        .all()
    )
    if not certificates:
        raise HTTPException(status_code=409, detail="No completed certificates available for download")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for certificate in certificates:
            if not certificate.file_path:
                continue
            file_path = Path(settings.CERTIFICATES_DIR) / certificate.file_path
            if file_path.exists():
                archive.write(file_path, arcname=f"{certificate.recipient_name}.pdf")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.zip"'},
    )
