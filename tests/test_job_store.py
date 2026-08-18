from unittest.mock import patch, MagicMock

from app.models import JobStatus, ReleaseDecision
from app.services import job_store


def _fake_analysis(decision=ReleaseDecision.APPROVE, risk_score=0.1):
    analysis = MagicMock()
    analysis.decision = decision
    analysis.risk_score = risk_score
    return analysis


def setup_function():
    # Each test starts from a clean slate; the store is a plain module-level
    # dict shared across tests, same as decision_history in decision_engine.
    job_store._jobs.clear()


def test_create_job_returns_unique_pending_job():
    job1 = job_store.create_job(repo="a/b", branch="main")
    job2 = job_store.create_job(repo="a/b", branch="main")

    assert job1.job_id != job2.job_id
    assert job1.status == JobStatus.PENDING


def test_get_job_returns_none_for_unknown_id():
    assert job_store.get_job("does-not-exist") is None


def test_run_analysis_job_marks_completed_on_success():
    job = job_store.create_job(repo="owner/repo", branch="main")

    with patch("app.services.job_store.analyze_release", return_value=_fake_analysis()):
        job_store.run_analysis_job(job.job_id, repo="owner/repo", branch="main")

    updated = job_store.get_job(job.job_id)
    assert updated.status == JobStatus.COMPLETED
    assert updated.result is not None
    assert updated.completed_at is not None


def test_run_analysis_job_marks_failed_on_exception():
    job = job_store.create_job(repo="owner/repo", branch="main")

    with patch("app.services.job_store.analyze_release", side_effect=RuntimeError("boom")):
        job_store.run_analysis_job(job.job_id, repo="owner/repo", branch="main")

    updated = job_store.get_job(job.job_id)
    assert updated.status == JobStatus.FAILED
    assert "boom" in updated.error


def test_run_analysis_job_posts_success_status_for_approve():
    job = job_store.create_job(repo="owner/repo", branch="main", commit_sha="deadbeef")

    with patch("app.services.job_store.analyze_release", return_value=_fake_analysis(ReleaseDecision.APPROVE)), \
         patch("app.services.job_store.post_commit_status") as mock_post:
        job_store.run_analysis_job(
            job.job_id, repo="owner/repo", branch="main", commit_sha="deadbeef", post_status=True,
        )

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["state"] == "success"
    assert kwargs["sha"] == "deadbeef"


def test_run_analysis_job_posts_failure_status_for_reject():
    job = job_store.create_job(repo="owner/repo", branch="main", commit_sha="deadbeef")

    with patch("app.services.job_store.analyze_release", return_value=_fake_analysis(ReleaseDecision.REJECT)), \
         patch("app.services.job_store.post_commit_status") as mock_post:
        job_store.run_analysis_job(
            job.job_id, repo="owner/repo", branch="main", commit_sha="deadbeef", post_status=True,
        )

    _, kwargs = mock_post.call_args
    assert kwargs["state"] == "failure"


def test_run_analysis_job_posts_error_status_on_crash():
    job = job_store.create_job(repo="owner/repo", branch="main", commit_sha="deadbeef")

    with patch("app.services.job_store.analyze_release", side_effect=RuntimeError("crashed")), \
         patch("app.services.job_store.post_commit_status") as mock_post:
        job_store.run_analysis_job(
            job.job_id, repo="owner/repo", branch="main", commit_sha="deadbeef", post_status=True,
        )

    _, kwargs = mock_post.call_args
    assert kwargs["state"] == "error"


def test_no_status_posted_when_post_status_false():
    job = job_store.create_job(repo="owner/repo", branch="main", commit_sha="deadbeef")

    with patch("app.services.job_store.analyze_release", return_value=_fake_analysis()), \
         patch("app.services.job_store.post_commit_status") as mock_post:
        job_store.run_analysis_job(
            job.job_id, repo="owner/repo", branch="main", commit_sha="deadbeef", post_status=False,
        )

    mock_post.assert_not_called()


def test_list_jobs_sorted_most_recent_first():
    job1 = job_store.create_job(repo="a", branch="main")
    job2 = job_store.create_job(repo="b", branch="main")

    jobs = job_store.list_jobs()
    assert jobs[0].job_id == job2.job_id or jobs[0].created_at >= jobs[-1].created_at
