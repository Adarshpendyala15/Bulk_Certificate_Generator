import io
import zipfile


def test_single_certificate_and_zip_downloads(client):
    payload = {
        "event_name": "Design Cohort",
        "issuer_name": "Studio One",
        "recipients": [
            {"name": "Ellis", "email": "ellis@example.com"},
            {"name": "Fiona", "email": "fiona@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]
    job_data = client.get(f"/api/v1/jobs/{job_id}").json()
    cert_id = job_data["certificates"][0]["id"]

    pdf_response = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert pdf_response.content.startswith(b"%PDF")

    zip_response = client.get(f"/api/v1/jobs/{job_id}/download")
    assert zip_response.status_code == 200
    assert zip_response.headers["content-type"].startswith("application/zip")

    with zipfile.ZipFile(io.BytesIO(zip_response.content)) as archive:
        assert len(archive.namelist()) == 2

    not_found = client.get("/api/v1/certificates/does-not-exist/download")
    assert not_found.status_code == 404

    missing_job = client.get("/api/v1/jobs/does-not-exist/download")
    assert missing_job.status_code == 404
