import json
from datetime import datetime
from app.models import (
    ReleaseAnalysis,
    ReleaseDecision,
    CommitData,
    TestResult,
    SecuritySummary,
)
from app.services.github_service import get_latest_commit, clone_repository, cleanup_repository
from app.services.test_service import run_tests, _get_simulated_tests
from app.services.security_service import run_security_scan, _get_simulated_scan
from app.services.ai_service import get_ai_evaluation
from app.utils.logger import logger
from app.config import GITHUB_REPO


# In-memory storage for decision history
decision_history: list = []


def analyze_release(repo: str = "", commit_id: str = "", branch: str = "main") -> ReleaseAnalysis:
    """Run full release analysis pipeline."""
    logger.info(f"Starting release analysis for repo: {repo or 'default'}, branch: {branch}")

    # Step 1: Get commit data
    commit_data = get_latest_commit(repo=repo, branch=branch)
    if not commit_data:
        commit_data = CommitData(
            commit_id="unknown",
            author="unknown",
            message="Could not fetch commit data",
            timestamp=datetime.now().isoformat(),
        )

    logger.info(f"Commit: {commit_data.commit_id} by {commit_data.author}")

    # Step 2 & 3: Clone the ACTUAL repo being analyzed and run tests/security
    # scans against it. Previously these were run with no directory argument,
    # which silently defaulted to ".", i.e. wherever the FastAPI server
    # process happened to be running -- the release-agent's OWN code, not
    # the repo the user asked about. That's why every analysis converged on
    # roughly the same score regardless of which repo was submitted.
    target_repo = repo or GITHUB_REPO
    clone_path = clone_repository(target_repo, branch) if target_repo else None

    try:
        scan_dir = clone_path or "."
        if clone_path:
            logger.info(f"Running tests & security scan against cloned repo at {clone_path}")
        else:
            logger.warning(
                "Could not clone target repo (private/unreachable/no repo specified); "
                "falling back to simulated results instead of scanning the wrong codebase"
            )

        # Step 2: Run tests
        test_results = run_tests(scan_dir) if clone_path else _get_simulated_tests()
        logger.info(f"Tests: {'PASSED' if test_results.passed else 'FAILED'} ({test_results.passed_tests}/{test_results.total_tests})")

        # Step 3: Run security scan
        security_results = run_security_scan(scan_dir) if clone_path else _get_simulated_scan()
        logger.info(f"Security: C={security_results.critical} H={security_results.high} M={security_results.medium} L={security_results.low}")
    finally:
        cleanup_repository(clone_path)

    # Step 4: AI evaluation
    ai_response = get_ai_evaluation(
        commit_data=commit_data.model_dump(),
        test_results=test_results.model_dump(),
        security_results=security_results.model_dump(),
    )

    # Parse AI response
    try:
        ai_result = json.loads(ai_response)
        decision_str = ai_result.get("decision", "hold").lower()
        risk_score = float(ai_result.get("risk_score", 0.5))
        reasoning = ai_result.get("reasoning", "")
        recommendations = ai_result.get("recommendations", [])
    except (json.JSONDecodeError, TypeError, ValueError):
        decision_str = "hold"
        risk_score = 0.5
        reasoning = ai_response if isinstance(ai_response, str) else "Unable to parse AI response"
        recommendations = []

    risk_score = max(0.0, min(1.0, risk_score))

    # Map to enum
    decision_map = {
        "approve": ReleaseDecision.APPROVE,
        "reject": ReleaseDecision.REJECT,
        "hold": ReleaseDecision.HOLD,
    }
    decision = decision_map.get(decision_str, ReleaseDecision.HOLD)

    # Build analysis result
    analysis = ReleaseAnalysis(
        commit_data=commit_data,
        test_results=test_results,
        security_results=security_results,
        risk_score=risk_score,
        decision=decision,
        ai_reasoning=reasoning,
        timestamp=datetime.now().isoformat(),
    )

    # Store in history
    history_entry = {
        "id": len(decision_history) + 1,
        "commit_id": commit_data.commit_id,
        "author": commit_data.author,
        "message": commit_data.message,
        "decision": decision.value,
        "risk_score": risk_score,
        "reasoning": reasoning,
        "recommendations": recommendations,
        "test_passed": test_results.passed,
        "security_critical": security_results.critical,
        "security_high": security_results.high,
        "timestamp": analysis.timestamp,
    }
    decision_history.append(history_entry)

    logger.info(f"Decision: {decision.value} (Risk: {risk_score})")

    return analysis


def get_decision_history() -> list:
    """Return the decision history."""
    return list(reversed(decision_history))


def get_dashboard_stats() -> dict:
    """Get aggregated stats for the dashboard."""
    total = len(decision_history)
    approved = sum(1 for d in decision_history if d["decision"] == "approve")
    rejected = sum(1 for d in decision_history if d["decision"] == "reject")
    held = sum(1 for d in decision_history if d["decision"] == "hold")

    avg_risk = (
        sum(d["risk_score"] for d in decision_history) / total
        if total > 0
        else 0.0
    )

    return {
        "total_analyses": total,
        "approved": approved,
        "rejected": rejected,
        "held": held,
        "average_risk_score": round(avg_risk, 2),
        "latest_decision": decision_history[-1] if decision_history else None,
    }
