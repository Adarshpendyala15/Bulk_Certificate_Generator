def test_create_job_returns_202_and_persists_rows(client):
    payload = {
        "event_name": "Summer Bootcamp",
        "issuer_name": "Acme Education",
        "issue_date": "2026-10-10",
        "recipients": [
            {"name": "Alice Example", "email": "alice@example.com", "course_or_role": "Python"},
            {"name": "Bob Example", "email": "bob@example.com", "course_or_role": "ML"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] in {"PENDING", "PROCESSING", "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"}
    assert body["total_count"] == 2
    assert body["job_id"]
    assert body["succeeded_count"] == 2
    assert body["failed_count"] == 0
    assert body["pending_count"] == 0
