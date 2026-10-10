# Bulk Certificate Generator

This project provides a FastAPI backend for generating bulk certificate PDFs from a list of recipients. It accepts a job payload, validates each recipient independently, creates per-certificate rows, and renders PDF files in the background while exposing job status and download endpoints.

## Overview

The service is built for high-volume certificate runs without blocking the HTTP request. A job is created quickly with a 202 Accepted response, then a background worker generates PDF files for each valid recipient, while invalid recipients are stored as FAILED rows with a clear error message. The API exposes endpoints for polling status, retrieving certificate metadata, downloading a single PDF, and downloading a ZIP bundle of all successful certificates.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   python -m pip install -r requirements.txt
3. Copy the sample env file and adjust values if needed:
   cp .env.example .env
4. Available environment variables:
   - DATABASE_URL: SQLite default, or PostgreSQL connection string such as postgresql+psycopg://user:pass@host/dbname
   - CERTIFICATES_DIR: directory for generated files
   - PROCESSING_MODE: async or sync
   - MAX_RECIPIENTS_PER_JOB: maximum recipients per job

## Run the app

Start the API with Uvicorn:

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Swagger UI and OpenAPI docs:

http://localhost:8000/docs

## Run tests

pytest -q

## Example curl commands

Submit a job:

curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Summer Bootcamp",
    "issuer_name": "Acme Education",
    "issue_date": "2026-10-10",
    "recipients": [
      {"name": "Alice Example", "email": "alice@example.com", "course_or_role": "Python"},
      {"name": "Bob Example", "email": "bob@example.com", "course_or_role": "Machine Learning"}
    ]
  }'

Poll job status:

curl http://localhost:8000/api/v1/jobs/<job_id>

Download a single certificate:

curl -L http://localhost:8000/api/v1/certificates/<certificate_id>/download -o certificate.pdf

Download all successful certificates for a job:

curl -L http://localhost:8000/api/v1/jobs/<job_id>/download -o certificates.zip

## Sample request and response

Request JSON:

{
  "event_name": "Spring Cohort",
  "issuer_name": "Northwind Academy",
  "issue_date": "2026-03-15",
  "recipients": [
    {"name": "Dana Lee", "email": "dana@example.com", "course_or_role": "Data Science"},
    {"name": "Evan Ross", "email": "evan@example.com", "course_or_role": "Product Design"}
  ]
}

Response JSON:

{
  "job_id": "3d7dc2d8-4f85-4cb9-b439-6b0a8e7462d8",
  "status": "PROCESSING",
  "total_count": 2,
  "succeeded_count": 0,
  "failed_count": 0,
  "pending_count": 2
}

## Design decisions

FastAPI was chosen because the project needs a lightweight API with automatic request validation, type-safe schemas, OpenAPI docs, and a clean Python interface for a backend service.

Background processing runs in a ThreadPoolExecutor instead of a synchronous request path because large certificate batches would otherwise block the HTTP request long enough to exceed practical timeouts. The API uses a 202 Accepted response and polling pattern so the client can check job status while generation continues.

Each certificate is generated and committed independently so that a single failure does not prevent other valid recipients from completing. A failed PDF generation leaves a FAILED row with an error message instead of aborting the entire job.

Invalid recipients become FAILED rows rather than rejecting the whole request because the business requirement is to keep valid certificates flowing while preserving auditability for bad input. This yields a more resilient bulk-processing workflow.

SQLite is the default database because it is simple to run locally and works well for development and tests. The configuration is URL-based so PostgreSQL can be used by changing only the DATABASE_URL value.

Files are stored on disk with the relative path recorded in the database. This avoids storing huge binary content directly in the database while keeping each PDF file easy to serve and archive.

Trade-offs and limitations: the in-process worker is lost on restart, so a production deployment would need a durable queue such as Celery or RQ plus managed storage such as S3 or a blob service. Idempotency and retry behavior are natural future enhancements, especially for partially completed jobs when the worker restarts or a downstream storage error occurs.
