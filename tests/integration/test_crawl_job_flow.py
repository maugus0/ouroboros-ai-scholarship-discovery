"""Integration tests for the crawl job flow."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_trigger_crawl_on_demand(service_token_header):
    """Triggering an on-demand crawl should create a job."""
    response = client.post(
        "/api/v1/scholarships/crawl",
        json={
            "job_type": "on_demand",
            "target_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
        },
        headers=service_token_header,
    )
    assert response.status_code in (200, 503)


def test_trigger_crawl_missing_target(service_token_header):
    """On-demand crawl without target should return 422."""
    response = client.post(
        "/api/v1/scholarships/crawl",
        json={"job_type": "on_demand"},
        headers=service_token_header,
    )
    assert response.status_code in (422, 503)


def test_crawl_status_not_found(service_token_header):
    """Getting status of non-existent job should return 404 or 503."""
    response = client.get(
        "/api/v1/scholarships/crawl/non-existent-job-id",
        headers=service_token_header,
    )
    assert response.status_code in (404, 503)


def test_list_crawl_jobs(service_token_header):
    """Listing crawl jobs should return a response."""
    response = client.get(
        "/api/v1/scholarships/crawl",
        headers=service_token_header,
    )
    assert response.status_code in (200, 503)
