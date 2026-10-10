import pytest


def test_rejects_empty_recipients(client):
    response = client.post(
        "/api/v1/jobs",
        json={"event_name": "Event", "issuer_name": "Issuer", "recipients": []},
    )
    assert response.status_code == 422


def test_rejects_too_many_recipients(client):
    recipients = [{"name": f"User {i}", "email": f"user{i}@example.com"} for i in range(1001)]
    response = client.post(
        "/api/v1/jobs",
        json={"event_name": "Event", "issuer_name": "Issuer", "recipients": recipients},
    )
    assert response.status_code == 422


def test_invalid_recipients_are_marked_failed(client):
    payload = {
        "event_name": "Event",
        "issuer_name": "Issuer",
        "recipients": [
            {"name": "   ", "email": "valid@example.com"},
            {"name": "Good User", "email": "bad-email"},
            {"name": "Duplicate", "email": "dup@example.com"},
            {"name": "Duplicate", "email": "dup@example.com"},
            {"name": "Valid User", "email": "valid2@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["total_count"] == 5
    assert body["failed_count"] >= 1
    assert body["succeeded_count"] >= 1
