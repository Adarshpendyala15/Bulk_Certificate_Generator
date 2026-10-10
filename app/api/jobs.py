from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JobCreateRequest, JobCreateResponse, JobDetailResponse
from app.services.job_service import create_job, get_job_detail

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.post("/jobs", status_code=202, response_model=JobCreateResponse)
def create_jobs(payload: JobCreateRequest, db: Session = Depends(get_db)):
    return create_job(db, payload)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def fetch_job(
    job_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return get_job_detail(db, job_id, status, limit, offset)
