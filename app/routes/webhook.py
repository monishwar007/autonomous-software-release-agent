import json
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks

from app.models import AnalysisRequest, JobStatus
from app.services.decision_engine import get_decision_history, get_dashboard_stats
from app.services import job_store
from app.utils.logger import logger
from app.utils.webhook_security import verify_github_signature
from app.config import WEBHOOK_SECRET

router = APIRouter()

# Event types this agent actually acts on. GitHub sends many other event
# types (issues, stars, releases, ...) to a webhook configured for "all
# events"; anything not in this set is acknowledged but ignored rather than
# erroring, since GitHub retries deliveries that don't get a 2xx response.
HANDLED_EVENTS = {"push"}


@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Real GitHub webhook endpoint.

    Verifies GitHub's HMAC-SHA256 signature, then queues analysis as a
    background job and returns immediately. GitHub expects a response
    within ~10 seconds and will mark the delivery failed (and may
    eventually disable the webhook after repeated timeouts) if this
    handler blocks until a full analysis finishes.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event = request.headers.get("X-GitHub-Event", "")

    if not verify_github_signature(raw_body, signature, WEBHOOK_SECRET):
        logger.warning("Rejected webhook delivery: invalid signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if not WEBHOOK_SECRET:
        logger.warning(
            "WEBHOOK_SECRET is not configured - signature verification is "
            "effectively disabled and this endpoint accepts unsigned "
            "requests. Set WEBHOOK_SECRET (and the same value in GitHub's "
            "webhook settings) before exposing this endpoint publicly."
        )

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if event == "ping":
        # GitHub sends this once when the webhook is first created, purely
        # to confirm the endpoint is reachable. Nothing to analyze.
        return {"status": "pong"}

    if event not in HANDLED_EVENTS:
        logger.info(f"Ignoring unhandled webhook event type: {event or '(missing)'}")
        return {"status": "ignored", "event": event}

    # A correctly signed body can still be the wrong shape (a JSON list, a
    # string, wrong field types). Reject those with a 400 instead of letting
    # an AttributeError surface as a 500.
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    repository = payload.get("repository") or {}
    if not isinstance(repository, dict):
        raise HTTPException(status_code=400, detail="Payload has an invalid 'repository' field")

    repo_name = repository.get("full_name", "")
    if not isinstance(repo_name, str):
        raise HTTPException(status_code=400, detail="Payload has an invalid 'repository.full_name' field")

    ref = payload.get("ref") or ""
    if not isinstance(ref, str):
        raise HTTPException(status_code=400, detail="Payload has an invalid 'ref' field")
    branch = ref.replace("refs/heads/", "") if ref else "main"

    head_commit = payload.get("head_commit") or {}
    if not isinstance(head_commit, dict):
        raise HTTPException(status_code=400, detail="Payload has an invalid 'head_commit' field")
    commit_sha = payload.get("after") or head_commit.get("id")
    if commit_sha is not None and not isinstance(commit_sha, str):
        raise HTTPException(status_code=400, detail="Payload has an invalid commit SHA")

    if not repo_name:
        raise HTTPException(status_code=400, detail="Payload missing repository information")

    job = job_store.create_job(repo=repo_name, branch=branch, commit_sha=commit_sha)
    background_tasks.add_task(
        job_store.run_analysis_job,
        job_id=job.job_id,
        repo=repo_name,
        branch=branch,
        commit_sha=commit_sha,
        post_status=True,
    )

    logger.info(f"Queued analysis job {job.job_id} for {repo_name}@{branch} (from GitHub webhook)")
    return {"status": "accepted", "job_id": job.job_id}


@router.post("/analyze")
async def trigger_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Manually trigger a release analysis.

    Returns a job_id immediately; poll GET /webhook/analyze/{job_id} for
    progress and the eventual result. A full analysis (clone + isolated
    venv + dependency install + pytest + bandit) can take anywhere from a
    few seconds to a couple of minutes depending on the repo, so this runs
    as a background job rather than blocking the HTTP request.
    """
    repo = request.repo_url or ""
    branch = request.branch or "main"

    job = job_store.create_job(repo=repo, branch=branch)
    background_tasks.add_task(
        job_store.run_analysis_job,
        job_id=job.job_id,
        repo=repo,
        branch=branch,
        commit_sha=None,
        post_status=False,
    )

    logger.info(f"Queued analysis job {job.job_id} for {repo or 'default repo'}")
    return {"status": "accepted", "job_id": job.job_id}


@router.get("/analyze/{job_id}")
async def get_analysis_result(job_id: str):
    """Poll the status (and, once available, the result) of a background
    analysis job created by POST /webhook/analyze or the GitHub webhook."""
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.job_id,
        "status": job.status.value,
        "repo": job.repo,
        "branch": job.branch,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }

    if job.status == JobStatus.COMPLETED and job.result:
        response["analysis"] = {
            "commit": job.result.commit_data.model_dump(),
            "tests": job.result.test_results.model_dump(),
            "security": job.result.security_results.model_dump(),
            "risk_score": job.result.risk_score,
            "decision": job.result.decision.value,
            "reasoning": job.result.ai_reasoning,
            "timestamp": job.result.timestamp,
        }
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error

    return response


@router.get("/history")
async def history():
    """Get decision history."""
    return {"history": get_decision_history()}


@router.get("/stats")
async def stats():
    """Get dashboard statistics."""
    return {"stats": get_dashboard_stats()}
