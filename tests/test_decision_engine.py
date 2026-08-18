import json
from unittest.mock import patch, MagicMock

from app.models import CommitData, TestResult, SecuritySummary
from app.services import decision_engine


def _commit():
    return CommitData(
        commit_id="abc12345", author="tester", message="test", timestamp="2026-01-01T00:00:00",
        files_changed=["a.py"], additions=5, deletions=1,
    )


def _tests(passed=True):
    return TestResult(passed=passed, total_tests=10, passed_tests=10 if passed else 8, failed_tests=0 if passed else 2)


def _security():
    return SecuritySummary(critical=0, high=0, medium=0, low=0, issues=[], scanned_files=5, duration=1.0)


def _ai_json(decision="approve", risk_score=0.1):
    return json.dumps({
        "decision": decision, "risk_score": risk_score,
        "reasoning": "test reasoning", "recommendations": [],
    })


def _patched_pipeline(**overrides):
    """Patch every external dependency of analyze_release() with sane
    defaults, so tests exercise only decision_engine's own orchestration
    logic (clamping, history bookkeeping, cleanup) -- not the real
    network/subprocess calls those dependencies would otherwise make."""
    defaults = dict(
        get_latest_commit=_commit(),
        clone_repository="/tmp/fake_clone",
        run_tests=_tests(),
        run_security_scan=_security(),
        get_ai_evaluation=_ai_json(),
    )
    defaults.update(overrides)
    return defaults


def test_risk_score_clamped_to_valid_range():
    """Regression/safety test: an AI response with an out-of-range risk
    score (bad model output, or a manually-crafted malicious response)
    must be clamped into [0, 1], not passed through raw."""
    values = _patched_pipeline(get_ai_evaluation=_ai_json(decision="reject", risk_score=5.0))
    with patch("app.services.decision_engine.get_latest_commit", return_value=values["get_latest_commit"]), \
         patch("app.services.decision_engine.clone_repository", return_value=values["clone_repository"]), \
         patch("app.services.decision_engine.cleanup_repository"), \
         patch("app.services.decision_engine.run_tests", return_value=values["run_tests"]), \
         patch("app.services.decision_engine.run_security_scan", return_value=values["run_security_scan"]), \
         patch("app.services.decision_engine.get_ai_evaluation", return_value=values["get_ai_evaluation"]):
        analysis = decision_engine.analyze_release(repo="owner/repo", branch="main")

    assert 0.0 <= analysis.risk_score <= 1.0


def test_malformed_ai_response_falls_back_to_hold():
    values = _patched_pipeline(get_ai_evaluation="not valid json at all")
    with patch("app.services.decision_engine.get_latest_commit", return_value=values["get_latest_commit"]), \
         patch("app.services.decision_engine.clone_repository", return_value=values["clone_repository"]), \
         patch("app.services.decision_engine.cleanup_repository"), \
         patch("app.services.decision_engine.run_tests", return_value=values["run_tests"]), \
         patch("app.services.decision_engine.run_security_scan", return_value=values["run_security_scan"]), \
         patch("app.services.decision_engine.get_ai_evaluation", return_value=values["get_ai_evaluation"]):
        analysis = decision_engine.analyze_release(repo="owner/repo", branch="main")

    assert analysis.decision.value == "hold"
    assert analysis.risk_score == 0.5


def test_cleanup_repository_always_called_even_on_failure():
    """The temp clone must always be cleaned up, even if a step in the
    middle of the pipeline (e.g. run_security_scan) raises."""
    values = _patched_pipeline()
    with patch("app.services.decision_engine.get_latest_commit", return_value=values["get_latest_commit"]), \
         patch("app.services.decision_engine.clone_repository", return_value=values["clone_repository"]), \
         patch("app.services.decision_engine.cleanup_repository") as mock_cleanup, \
         patch("app.services.decision_engine.run_tests", return_value=values["run_tests"]), \
         patch("app.services.decision_engine.run_security_scan", side_effect=Exception("scan crashed")):
        try:
            decision_engine.analyze_release(repo="owner/repo", branch="main")
        except Exception:
            pass

    mock_cleanup.assert_called_once_with("/tmp/fake_clone")


def test_no_clonable_repo_uses_simulated_fallbacks():
    """When cloning fails/isn't possible, the pipeline must use simulated
    test/security results rather than silently scanning '.' (the
    release-agent's own code) -- that was the original root bug."""
    values = _patched_pipeline(clone_repository=None)
    with patch("app.services.decision_engine.get_latest_commit", return_value=values["get_latest_commit"]), \
         patch("app.services.decision_engine.clone_repository", return_value=None), \
         patch("app.services.decision_engine.cleanup_repository"), \
         patch("app.services.decision_engine.run_tests") as mock_run_tests, \
         patch("app.services.decision_engine.run_security_scan") as mock_run_scan, \
         patch("app.services.decision_engine.get_ai_evaluation", return_value=values["get_ai_evaluation"]):
        decision_engine.analyze_release(repo="owner/repo", branch="main")

    # run_tests/run_security_scan (which take a real directory) must NOT
    # have been called with no clone available -- simulated fallbacks are
    # used instead.
    mock_run_tests.assert_not_called()
    mock_run_scan.assert_not_called()


def test_decision_history_grows_and_stats_update():
    decision_engine.decision_history.clear()
    values = _patched_pipeline()
    with patch("app.services.decision_engine.get_latest_commit", return_value=values["get_latest_commit"]), \
         patch("app.services.decision_engine.clone_repository", return_value=values["clone_repository"]), \
         patch("app.services.decision_engine.cleanup_repository"), \
         patch("app.services.decision_engine.run_tests", return_value=values["run_tests"]), \
         patch("app.services.decision_engine.run_security_scan", return_value=values["run_security_scan"]), \
         patch("app.services.decision_engine.get_ai_evaluation", return_value=values["get_ai_evaluation"]):
        decision_engine.analyze_release(repo="owner/repo", branch="main")
        decision_engine.analyze_release(repo="owner/repo", branch="main")

    history = decision_engine.get_decision_history()
    assert len(history) == 2
    # Most recent first
    assert history[0]["id"] == 2

    stats = decision_engine.get_dashboard_stats()
    assert stats["total_analyses"] == 2
    assert stats["approved"] == 2
