import os


def test_certificate_files_are_created(client):
    payload = {
        "event_name": "Python Bootcamp",
        "issuer_name": "Open Academy",
        "issue_date": "2026-06-01",
        "recipients": [
            {"name": "Cora Developer", "email": "cora@example.com", "course_or_role": "Backend"},
            {"name": "Drew Engineer", "email": "drew@example.com", "course_or_role": "API"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_response = client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["total_count"] == 2
    assert data["succeeded_count"] == 2

    certs = data["certificates"]
    assert len(certs) == 2
    for cert in certs:
        file_path = cert["file_path"]
        assert file_path
        assert os.path.exists(file_path)
        with open(file_path, "rb") as fh:
            data = fh.read()
        assert len(data) > 0
        assert data.startswith(b"%PDF")
