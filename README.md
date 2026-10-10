# Bulk Certificate Generator

A bulk certificate generation system built with **Python, FastAPI, and a relational database**. The application accepts a list of recipients in a single request, validates their information, generates personalized PDF certificates, tracks generation progress, and provides endpoints to download individual certificates or a ZIP archive of successful certificates.

## Key Features

- **Bulk Generation:** Generate certificates for multiple recipients through a single API request.
- **Recipient Validation:** Validate recipient information independently and record invalid entries.
- **PDF Generation:** Create personalized certificates using a predefined certificate template.
- **Background Processing:** Process large certificate batches without keeping the initial HTTP request open.
- **Job Tracking:** Monitor job status, total recipients, successful generations, failed generations, and pending work.
- **Failure Isolation:** Continue processing other recipients when an individual certificate fails.
- **Certificate Downloads:** Retrieve individual PDF certificates or download all successful certificates for a job as a ZIP archive.
- **Relational Database:** Persist job and certificate metadata.
- **Automated Tests:** Verify API behavior, input validation, generation, status tracking, and error handling.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| SQLAlchemy | Database interaction |
| SQLite | Default relational database |
| Pydantic | Request data validation |
| Uvicorn | ASGI application server |
| Pytest | Automated testing |
| ThreadPoolExecutor | Background certificate processing |
| PDF generation libraries | Creating personalized PDF certificates |
| JavaScript / Node.js | Supporting project components, where applicable |

The database can also be configured to use PostgreSQL through the `DATABASE_URL` environment variable.

## Project Structure

```text
Bulk_Certificate_Generator/
├── app/                     # FastAPI backend
├── frontend/                # Frontend application
├── node_certificates/       # Certificate-related files
├── tests/                   # Automated tests
├── tmp_certificates/        # Temporary certificate output
├── .env.example             # Environment configuration example
├── .gitignore
├── package.json             # Node.js project configuration
├── package-lock.json
├── requirements.txt         # Python dependencies
├── server.js                # Node.js entry point
└── README.md
```

*This is a high-level overview of the repository. The exact responsibilities of individual files depend on their implementation.*

## Prerequisites

Install the following before running the application:

- Python 3.10 or later
- pip
- Git
- Node.js and npm if you need to run the frontend or Node.js components

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Adarshpendyala15/Bulk_Certificate_Generator.git
cd Bulk_Certificate_Generator
```

### 2. Create a Python virtual environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`.

On Linux / macOS:

```bash
cp .env.example .env
```

On Windows Command Prompt:

```cmd
copy .env.example .env
```

Configure the required values as appropriate for your environment:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Database connection string; SQLite is the default |
| `CERTIFICATES_DIR` | Directory used to store generated certificates |
| `PROCESSING_MODE` | Processing configuration, such as `async` or `sync` |
| `MAX_RECIPIENTS_PER_JOB` | Maximum recipients allowed in a single job |

Use the exact defaults and supported values defined in `.env.example` and the application configuration.

### 5. Start the backend

From the repository root, run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend should be accessible at:

- **API base URL:** `http://localhost:8000`
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

Swagger UI allows you to explore the endpoints and submit requests interactively.

## API Endpoints

The API uses the `/api/v1` prefix for its main endpoints.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/jobs` | Submit a bulk certificate generation job |
| `GET` | `/api/v1/jobs/{job_id}` | Retrieve job status and progress |
| `GET` | `/api/v1/certificates/{certificate_id}/download` | Download an individual certificate |
| `GET` | `/api/v1/jobs/{job_id}/download` | Download successful certificates as a ZIP archive |

## Usage

### 1. Submit a bulk generation request

Send a `POST` request to `/api/v1/jobs`.

**Example using cURL:**

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Summer Bootcamp",
    "issuer_name": "Acme Education",
    "issue_date": "2026-10-10",
    "recipients": [
      {
        "name": "Alice Example",
        "email": "alice@example.com",
        "course_or_role": "Python"
      },
      {
        "name": "Bob Example",
        "email": "bob@example.com",
        "course_or_role": "Machine Learning"
      }
    ]
  }'
```

The request contains event information and multiple recipients, each with their own details.

A successful submission returns **HTTP 202 Accepted** and a job identifier.

Example response:

```json
{
  "job_id": "3d7dc2d8-4f85-4cb9-b439-6b0a8e7462d8",
  "status": "PROCESSING",
  "total_count": 2,
  "succeeded_count": 0,
  "failed_count": 0,
  "pending_count": 2
}
```

Use the returned `job_id` to monitor processing.

### 2. Check job status and progress

Send a `GET` request using the job identifier:

```bash
curl http://localhost:8000/api/v1/jobs/3d7dc2d8-4f85-4cb9-b439-6b0a8e7462d8
```

The response provides the job's current status and recipient counts.

- `total_count`: Total number of recipients.
- `succeeded_count`: Number of successfully generated certificates.
- `failed_count`: Number of failed certificate generations.
- `pending_count`: Number of recipients still awaiting completion.

Poll this endpoint periodically until the job reaches a terminal status.

### 3. Download an individual certificate

Use the certificate ID returned by the application's certificate metadata or results.

```bash
curl -L \
  http://localhost:8000/api/v1/certificates/CERTIFICATE_ID/download \
  -o certificate.pdf
```

Replace `CERTIFICATE_ID` with the actual certificate identifier.

### 4. Download all successful certificates

To retrieve a ZIP archive containing the successful certificates for a job:

```bash
curl -L \
  http://localhost:8000/api/v1/jobs/JOB_ID/download \
  -o certificates.zip
```

Replace `JOB_ID` with the identifier returned when the job was created.

The ZIP download is useful when processing large batches because the client can retrieve multiple certificates with a single request.

## Processing Workflow

1. The client submits one request containing event details and a recipient list.
2. FastAPI validates the incoming request.
3. The application creates a job and records individual certificate-generation entries.
4. The API returns a job ID so the client can track the request.
5. Background processing generates certificates for eligible recipients.
6. Each certificate is processed independently, and its result is recorded.
7. The job's progress and final status are updated.
8. The client retrieves individual certificates or downloads a ZIP archive.

## Validation and Failure Handling

The system is designed to isolate individual certificate failures rather than abort an entire batch.

- Invalid recipient data is recorded as a failed entry with an explanatory error message.
- A failure while generating one PDF should not prevent other valid recipients from being processed.
- Successful and failed results are tracked separately.
- Job-level progress reflects the outcomes of individual recipients.
- Invalid job IDs and certificate IDs should return appropriate HTTP error responses.

This approach makes it easier to identify problematic records and understand the outcome of a bulk request.

## Database and Storage

The application uses a relational database to store job information, recipient details, certificate-generation statuses, and references to generated files.

SQLite is the default choice for local development. PostgreSQL can be configured through `DATABASE_URL` for deployments that require a server-based relational database.

Generated PDF files are stored on disk, while their paths or references are maintained in the database. This avoids storing the entire PDF content as database records.

## Running Tests

Run the test suite from the project root with the Python virtual environment activated:

```bash
pytest -q
```

For more detailed test output:

```bash
pytest -v
```

The tests should cover the core requirements:

- Creating a generation job.
- Validating recipient input.
- Generating certificates.
- Checking job status and progress.
- Handling individual certificate-generation failures.
- Retrieving generated certificates.
- Downloading the ZIP archive, if covered by the test suite.

Run the tests before submitting changes to verify that the application's expected behavior remains intact.

## Design Decisions

### FastAPI for the backend

FastAPI provides automatic request validation, typed request and response schemas, and interactive API documentation. These capabilities make it suitable for a REST API that accepts structured bulk-generation requests.

### Background processing

Certificate generation can be time-consuming when a request contains many recipients. Background processing allows the API to return a job identifier without waiting for every certificate to finish.

The client can poll for progress separately instead of holding the original HTTP request open.

### Independent certificate generation

Each recipient is processed independently so a single failure does not unnecessarily interrupt the entire batch. This also enables the application to report meaningful per-recipient results.

### Relational database

A relational database maintains the association between a generation job and its individual certificate records. This makes job tracking and progress reporting straightforward.

### File-based certificate storage

PDF files are stored separately from database metadata. This reduces database storage overhead and supports individual downloads and ZIP packaging.

### Processing trade-offs

The current in-process background-processing approach is suitable for a local project and demonstration. However, tasks can be interrupted if the application process restarts.

For a production deployment, a durable queue such as Celery or RQ, retry handling, and managed file storage could improve reliability and scalability.

## Future Improvements

- Introduce a durable background task queue.
- Add retry mechanisms for transient failures.
- Support idempotency to prevent accidental duplicate jobs.
- Add authentication and authorization.
- Store certificates in cloud object storage.
- Add bulk-download size limits and streaming ZIP generation.
- Add structured logging and monitoring.
- Add certificate verification using unique IDs or QR codes.

## License

No license is specified here. Add a `LICENSE` file if you intend to distribute the project under an open-source license.

## Author

**Adarsh Pendyala**

GitHub: [Adarshpendyala15](https://github.com/Adarshpendyala15)

Repository: [Bulk Certificate Generator](https://github.com/Adarshpendyala15/Bulk_Certificate_Generator)
