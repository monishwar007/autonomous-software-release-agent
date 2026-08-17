import uuid
import threading
from datetime import datetime
from typing import Optional, Dict, List

from app.models import AnalysisJob, JobStatus
from app.services.decision_engine import analyze_release
from app.services.github_service import post_commit_status
from app.utils.logger import logger

# In-memory job store. Like decision_history in decision_engine, this
# resets on restart -- acceptable for this project's scope, but a real
# deployment would back this with a database so jobs/history survive
# restarts and can be shared across multiple worker processes.
_jobs: Dict[str, AnalysisJob] = {}
_lock = threading.Lock()

# GitHub's Statuses API only supports 4 states: error, failure, pending,
# success -- there's no built-in "needs human review" state. HOLD is
# conservatively mapped to "failure" so it blocks merges the same way
# REJECT does, until a human reviews and re-runs or overrides it. If your
# workflow would rather treat HOLD as non-blocking, change this mapping.
DECISION_TO_GITHUB_STATE = {
    "approve": "success",
    "reject": "failure",
    "hold": "failure",
}


def create_job(repo: str, branch: str, commit_sha: Optional[str] = None) -> AnalysisJob:
    """Register a new pending analysis job and return it immediately."""
    job = AnalysisJob(
        job_id=str(uuid.uuid4()),
        status=JobStatus.PENDING,
        repo=repo,
        branch=branch,
        commit_sha=commit_sha,
        created_at=datetime.now().isoformat(),
    )
    with _lock:
        _jobs[job.job_id] = job
    return job


def get_job(job_id: str) -> Optional[AnalysisJob]:
    with _lock:
        return _jobs.get(job_id)


def list_jobs() -> List[AnalysisJob]:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)


def run_analysis_job(
    job_id: str,
    repo: str,
    branch: str,
    commit_sha: Optional[str] = None,
    post_status: bool = False,
) -> None:
    """Runs the (blocking, potentially slow) analysis pipeline and updates
    the job record with the outcome. Meant to be scheduled via FastAPI's
    BackgroundTasks, which runs sync callables like this one in a
    threadpool so it doesn't block the event loop -- the HTTP response
    that queued this job has already been returned by the time this runs.

    When post_status is set (used for the GitHub webhook path), also posts
    the resulting decision back to GitHub as a commit status check on
    commit_sha -- this is what makes the decision actionable directly on
    GitHub (e.g. as a required check on a PR) instead of only visible
    through this API.
    """
    job = get_job(job_id)
    if job is None:
        logger.error(f"Job {job_id} vanished before it could run")
        return

    with _lock:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()

    try:
        analysis = analyze_release(repo=repo, branch=branch)
        with _lock:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now().isoformat()
            job.result = analysis

        logger.info(f"Job {job_id} completed: {analysis.decision.value} (risk {analysis.risk_score})")

        if post_status and commit_sha and repo:
            state = DECISION_TO_GITHUB_STATE.get(analysis.decision.value, "failure")
            description = f"{analysis.decision.value.upper()} - risk {analysis.risk_score:.2f}"
            post_commit_status(repo=repo, sha=commit_sha, state=state, description=description)

    except Exception as e:
        logger.error(f"Analysis job {job_id} failed: {e}")
        with _lock:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now().isoformat()
            job.error = str(e)

        if post_status and commit_sha and repo:
            post_commit_status(
                repo=repo,
                sha=commit_sha,
                state="error",
                description=f"Release agent analysis crashed: {e}",
            )
