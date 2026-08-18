import subprocess
import json
from unittest.mock import patch, MagicMock

from app.services import security_service


def _fake_result(stdout: str, returncode: int = 1):
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    return result


def _bandit_json(metrics: dict, results: list) -> str:
    return json.dumps({"errors": [], "metrics": metrics, "results": results})


def test_parses_clean_bandit_json():
    payload = _bandit_json(
        metrics={"file_a.py": {}, "file_b.py": {}, "_totals": {}},
        results=[],
    )
    fake = _fake_result(payload)
    with patch("app.services.security_service.subprocess.run", return_value=fake):
        result = security_service.run_security_scan("/some/repo")

    assert result.critical == 0
    assert result.scanned_files == 2  # 3 metric keys minus "_totals"


def test_counts_issues_by_severity():
    payload = _bandit_json(
        metrics={"a.py": {}, "_totals": {}},
        results=[
            {"issue_severity": "HIGH", "issue_text": "x", "filename": "a.py",
             "line_number": 1, "code": "", "test_id": "B101"},
            {"issue_severity": "medium", "issue_text": "y", "filename": "a.py",
             "line_number": 2, "code": "", "test_id": "B102"},
            {"issue_severity": "low", "issue_text": "z", "filename": "a.py",
             "line_number": 3, "code": "", "test_id": "B103"},
        ],
    )
    fake = _fake_result(payload)
    with patch("app.services.security_service.subprocess.run", return_value=fake):
        result = security_service.run_security_scan("/some/repo")

    assert result.high == 1
    assert result.medium == 1
    assert result.low == 1
    assert len(result.issues) == 3


def test_progress_bar_prefix_does_not_break_json_parsing():
    """Regression test: newer bandit versions print a progress bar to
    stdout BEFORE the JSON report (e.g. 'Working... [====] 100%'). This
    used to silently break json.loads(), making every scan report zero
    issues and a hardcoded scanned_files fallback regardless of the repo."""
    payload = _bandit_json(
        metrics={"x.py": {}, "y.py": {}, "y2.py": {}, "_totals": {}},
        results=[
            {"issue_severity": "critical", "issue_text": "bad", "filename": "x.py",
             "line_number": 5, "code": "", "test_id": "B999"},
        ],
    )
    stdout_with_progress_bar = "Working... \u2501\u2501\u2501\u2501 100% 0:00:01\n" + payload
    fake = _fake_result(stdout_with_progress_bar)

    with patch("app.services.security_service.subprocess.run", return_value=fake):
        result = security_service.run_security_scan("/some/repo")

    assert result.critical == 1
    assert result.scanned_files == 3  # must not fall back to a hardcoded value


def test_scanned_files_uses_totals_not_nonexistent_summary_key():
    """Regression test: the old code looked for metrics['_summary'], which
    bandit's JSON output does not have (the real key is '_totals'), so
    scanned_files silently fell back to 0 or a hardcoded value every time."""
    payload = _bandit_json(
        metrics={"f1.py": {}, "f2.py": {}, "f3.py": {}, "f4.py": {}, "_totals": {"loc": 500}},
        results=[],
    )
    fake = _fake_result(payload)
    with patch("app.services.security_service.subprocess.run", return_value=fake):
        result = security_service.run_security_scan("/some/repo")

    assert result.scanned_files == 4


def test_malformed_json_does_not_crash():
    fake = _fake_result("not even close to json {{{")
    with patch("app.services.security_service.subprocess.run", return_value=fake):
        result = security_service.run_security_scan("/some/repo")

    assert result.critical == 0
    assert result.issues == []


def test_bandit_not_installed_falls_back_to_simulated():
    with patch("app.services.security_service.subprocess.run", side_effect=FileNotFoundError):
        result = security_service.run_security_scan("/some/repo")

    assert result.scanned_files == 47  # the documented simulated fallback


def test_timeout_falls_back_to_simulated():
    with patch(
        "app.services.security_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="bandit", timeout=60),
    ):
        result = security_service.run_security_scan("/some/repo")

    assert result.scanned_files == 47
