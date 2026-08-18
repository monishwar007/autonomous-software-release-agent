import json
from unittest.mock import patch, MagicMock

from app.services import ai_service


def _commit(files=None, additions=10, deletions=5):
    return {
        "author": "tester",
        "message": "test commit",
        "files_changed": files or ["src/main.py"],
        "additions": additions,
        "deletions": deletions,
    }


def _tests(passed=True, failed=0, total=10):
    return {"passed": passed, "total_tests": total, "passed_tests": total - failed, "failed_tests": failed}


def _security(critical=0, high=0, medium=0, low=0):
    return {"critical": critical, "high": high, "medium": medium, "low": low}


def test_clean_commit_approved():
    result = json.loads(
        ai_service._rule_based_evaluation(_commit(), _tests(), _security())
    )
    assert result["decision"] == "approve"
    assert result["risk_score"] < 0.4


def test_critical_security_issue_forces_reject():
    result = json.loads(
        ai_service._rule_based_evaluation(_commit(), _tests(), _security(critical=1))
    )
    assert result["decision"] == "reject"
    assert "critical" in " ".join(result["recommendations"]).lower()


def test_failing_tests_increase_risk_and_are_recommended():
    result = json.loads(
        ai_service._rule_based_evaluation(_commit(), _tests(passed=False, failed=4, total=10), _security())
    )
    assert result["risk_score"] > 0.0
    assert any("failing tests" in r.lower() for r in result["recommendations"])


def test_sensitive_module_filenames_increase_risk():
    low_risk = json.loads(
        ai_service._rule_based_evaluation(
            _commit(files=["src/utils/formatting.py"]), _tests(), _security()
        )
    )
    high_risk = json.loads(
        ai_service._rule_based_evaluation(
            _commit(files=["src/auth/login.py", "src/payment/checkout.py"]), _tests(), _security()
        )
    )
    assert high_risk["risk_score"] > low_risk["risk_score"]


def test_large_changeset_increases_risk():
    small = json.loads(
        ai_service._rule_based_evaluation(_commit(files=["a.py"]), _tests(), _security())
    )
    large = json.loads(
        ai_service._rule_based_evaluation(
            _commit(files=[f"file_{i}.py" for i in range(15)]), _tests(), _security()
        )
    )
    assert large["risk_score"] > small["risk_score"]


def test_risk_score_never_exceeds_one():
    result = json.loads(
        ai_service._rule_based_evaluation(
            _commit(files=[f"auth/payment/security_{i}.py" for i in range(20)]),
            _tests(passed=False, failed=10, total=10),
            _security(critical=5, high=5, medium=5, low=5),
        )
    )
    assert result["risk_score"] <= 1.0


def test_no_groq_available_uses_rule_based():
    with patch.object(ai_service, "HAS_GROQ", False):
        result_str = ai_service.get_ai_evaluation(_commit(), _tests(), _security())
    result = json.loads(result_str)
    assert result["decision"] in ("approve", "reject", "hold")


def test_empty_groq_response_falls_back_without_crashing():
    """Regression test for a NameError bug: the empty-response fallback
    path referenced undefined variable names (github_data/test_data/
    security_data instead of the actual parameter names), which meant this
    exact scenario used to crash instead of falling back gracefully."""
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content=""))]
    fake_client.chat.completions.create.return_value = fake_response

    with patch.object(ai_service, "HAS_GROQ", True), \
         patch.object(ai_service, "GROQ_API_KEY", "fake-key"), \
         patch.object(ai_service, "Groq", return_value=fake_client):
        # Must not raise NameError
        result_str = ai_service.get_ai_evaluation(_commit(), _tests(), _security())

    result = json.loads(result_str)
    assert result["decision"] in ("approve", "reject", "hold")


def test_groq_exception_falls_back_to_rule_based():
    with patch.object(ai_service, "HAS_GROQ", True), \
         patch.object(ai_service, "GROQ_API_KEY", "fake-key"), \
         patch.object(ai_service, "Groq", side_effect=Exception("network error")):
        result_str = ai_service.get_ai_evaluation(_commit(), _tests(), _security())

    result = json.loads(result_str)
    assert result["decision"] in ("approve", "reject", "hold")
