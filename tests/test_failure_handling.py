from app.services import certificate_generator


def test_individual_failure_does_not_block_others(client, monkeypatch):
    original = certificate_generator.generate_certificate_pdf

    def flaky(job_id, cert_id, name, event_name, issuer_name, issue_date, course_or_role):
        if name == "Brittany":
            raise RuntimeError("forced failure")
        return original(job_id, cert_id, name, event_name, issuer_name, issue_date, course_or_role)

    monkeypatch.setattr(certificate_generator, "generate_certificate_pdf", flaky)

    payload = {
        "event_name": "Cloud Workshop",
        "issuer_name": "Northwind",
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Brittany", "email": "brittany@example.com"},
            {"name": "Casey", "email": "casey@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["total_count"] == 3
    assert body["failed_count"] == 1
    assert body["succeeded_count"] == 2

    job = client.get(f"/api/v1/jobs/{body['job_id']}").json()
    assert job["status"] == "COMPLETED_WITH_ERRORS"
    assert job["failed_count"] == 1
    assert job["succeeded_count"] == 2
