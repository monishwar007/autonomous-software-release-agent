import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import JobStatus


@pytest.fixture
def client():
    return TestClient(app)


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_ping_event_short_circuits(client):
    response = client.post(
        "/webhook/github", json={"zen": "hi"}, headers={"X-GitHub-Event": "ping"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pong"


def test_unhandled_event_type_is_ignored_not_errored(client):
    response = client.post(
        "/webhook/github", json={"action": "opened"}, headers={"X-GitHub-Event": "issues"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_push_missing_repository_returns_400(client):
    response = client.post(
        "/webhook/github", json={"ref": "refs/heads/main"}, headers={"X-GitHub-Event": "push"}
    )
    assert response.status_code == 400


def test_push_with_wrong_signature_is_rejected(client):
    body = json.dumps({"ref": "refs/heads/main", "repository": {"full_name": "a/b"}}).encode()
    with patch("app.routes.webhook.WEBHOOK_SECRET", "correct-secret"):
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": "sha256=wrongsignature",
                "Content-Type": "application/json",
            },
        )
    assert response.status_code == 401


def test_push_with_correct_signature_queues_job(client):
    body = json.dumps({
        "ref": "refs/heads/main",
        "repository": {"full_name": "owner/repo"},
        "after": "deadbeef",
    }).encode()
    signature = _sign(body, "correct-secret")

    with patch("app.routes.webhook.WEBHOOK_SECRET", "correct-secret"), \
         patch("app.services.job_store.run_analysis_job") as mock_run:
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["repo"] == "owner/repo"
    assert kwargs["commit_sha"] == "deadbeef"
    assert kwargs["post_status"] is True


def test_manual_analyze_returns_job_id_immediately(client):
    with patch("app.services.job_store.run_analysis_job") as mock_run:
        response = client.post("/webhook/analyze", json={"repo_url": "owner/repo", "branch": "main"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data
    _, kwargs = mock_run.call_args
    assert kwargs["post_status"] is False  # manual trigger never posts back to GitHub


def test_poll_unknown_job_returns_404(client):
    response = client.get("/webhook/analyze/does-not-exist")
    assert response.status_code == 404


def test_poll_completed_job_returns_analysis(client):
    from app.services import job_store as job_store_module
    from app.models import CommitData, TestResult, SecuritySummary, ReleaseAnalysis, ReleaseDecision

    job = job_store_module.create_job(repo="owner/repo", branch="main")
    job.status = JobStatus.COMPLETED
    job.result = ReleaseAnalysis(
        commit_data=CommitData(commit_id="abc", author="x", message="y", timestamp="2026-01-01"),
        test_results=TestResult(passed=True, total_tests=5, passed_tests=5, failed_tests=0),
        security_results=SecuritySummary(),
        risk_score=0.1,
        decision=ReleaseDecision.APPROVE,
        ai_reasoning="looks fine",
        timestamp="2026-01-01",
    )

    response = client.get(f"/webhook/analyze/{job.job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["analysis"]["decision"] == "approve"


def test_history_and_stats_endpoints_still_work(client):
    assert client.get("/webhook/history").status_code == 200
    assert client.get("/webhook/stats").status_code == 200
