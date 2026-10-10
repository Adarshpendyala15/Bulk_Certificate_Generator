def test_job_status_counts_progress_and_pagination(client):
    payload = {
        "event_name": "Quarterly Workshop",
        "issuer_name": "SkillForge",
        "recipients": [
            {"name": "Ava", "email": "ava@example.com"},
            {"name": "Ben", "email": "ben@example.com"},
            {"name": "Cleo", "email": "cleo@example.com"},
            {"name": "Dane", "email": "dane@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    status_response = client.get(f"/api/v1/jobs/{job_id}?limit=2&offset=1")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["job_id"] == job_id
    assert data["total_count"] == 4
    assert data["succeeded_count"] == 4
    assert data["progress_percentage"] == 100.0
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["offset"] == 1
    assert len(data["certificates"]) == 2

    filtered = client.get(f"/api/v1/jobs/{job_id}?status=SUCCESS")
    assert filtered.status_code == 200
    assert len(filtered.json()["certificates"]) == 4

    missing = client.get("/api/v1/jobs/not-a-real-job")
    assert missing.status_code == 404
