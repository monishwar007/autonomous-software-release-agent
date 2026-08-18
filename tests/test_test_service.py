import subprocess
from unittest.mock import patch, MagicMock

from app.services import test_service


def _fake_result(stdout: str, returncode: int = 0, stderr: str = ""):
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


def test_all_passed():
    fake = _fake_result("...\n5 passed in 1.23s\n")
    with patch("app.services.test_service.subprocess.run", return_value=fake):
        result = test_service.run_tests(".")

    assert result.passed is True
    assert result.total_tests == 5
    assert result.passed_tests == 5
    assert result.failed_tests == 0


def test_mixed_pass_and_fail():
    fake = _fake_result("...\n3 passed, 2 failed in 0.42s\n")
    with patch("app.services.test_service.subprocess.run", return_value=fake):
        result = test_service.run_tests(".")

    assert result.passed is False
    assert result.total_tests == 5
    assert result.passed_tests == 3
    assert result.failed_tests == 2


def test_no_tests_collected_is_not_fabricated_as_a_pass():
    """Regression test for the original bug: when pytest collects 0 tests,
    the code used to report a fabricated '12/12 passed' result. It must
    now honestly report zero tests, not invent a suspiciously-consistent
    pass count."""
    fake = _fake_result("collected 0 items\n\nno tests ran in 0.09s\n")
    with patch("app.services.test_service.subprocess.run", return_value=fake):
        result = test_service.run_tests(".")

    assert result.total_tests == 0
    assert result.passed_tests == 0
    assert result.failed_tests == 0
    # Must NOT be the old hardcoded fabricated values
    assert result.total_tests != 12
    assert result.passed_tests != 12


def test_collection_error_reported_honestly_not_as_zero_zero_pass():
    """When pytest can't even collect tests (e.g. missing dependency),
    this must be distinguishable in raw_output from a genuine 0-test repo,
    and must not be silently treated as a clean pass."""
    fake = _fake_result(
        "ImportError while loading conftest.py\n"
        "ModuleNotFoundError: No module named 'flask'\n",
        returncode=4,
    )
    with patch("app.services.test_service.subprocess.run", return_value=fake):
        result = test_service.run_tests(".")

    assert result.total_tests == 0
    assert "could not be collected" in result.raw_output.lower()


def test_pytest_not_installed_falls_back_to_simulated():
    with patch("app.services.test_service.subprocess.run", side_effect=FileNotFoundError):
        result = test_service.run_tests(".")

    assert result.raw_output.startswith("Simulated:")
    assert 15 <= result.total_tests <= 30


def test_timeout_falls_back_to_simulated():
    with patch(
        "app.services.test_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=120),
    ):
        result = test_service.run_tests(".")

    assert result.raw_output.startswith("Simulated:")


def test_uses_isolated_venv_for_real_repo_paths():
    """When analyzing an actual cloned repo (test_dir != '.'), an isolated
    virtualenv must be built and used, rather than running pytest directly
    against the release-agent's own environment (which is the exact bug
    that let one analyzed repo corrupt the host app's dependencies)."""
    fake_result = _fake_result("2 passed in 0.10s\n")

    with patch(
        "app.services.test_service._build_isolated_env",
        return_value=("/tmp/fake_venv", "/tmp/fake_venv/bin/python"),
    ) as mock_build_env, patch(
        "app.services.test_service.subprocess.run", return_value=fake_result
    ) as mock_run, patch(
        "app.services.test_service.shutil.rmtree"
    ):
        result = test_service.run_tests("/tmp/some_cloned_repo")

    mock_build_env.assert_called_once_with("/tmp/some_cloned_repo")
    # The pytest invocation must use the isolated venv's python, not the
    # host environment's bare "pytest" command.
    called_cmd = mock_run.call_args[0][0]
    assert called_cmd[0] == "/tmp/fake_venv/bin/python"
    assert result.passed_tests == 2


def test_local_dir_skips_isolated_venv():
    """test_dir='.' (the demo/no-clone path) should not pay the cost of
    building a throwaway venv."""
    fake_result = _fake_result("1 passed in 0.01s\n")
    with patch(
        "app.services.test_service._build_isolated_env"
    ) as mock_build_env, patch(
        "app.services.test_service.subprocess.run", return_value=fake_result
    ):
        test_service.run_tests(".")

    mock_build_env.assert_not_called()
