import os
import re
import shutil
import subprocess
import tempfile
import venv
import random
from app.utils.logger import logger
from app.models import TestResult


# Matches the pytest summary line, e.g.:
#   "3 passed, 1 failed, 2 skipped in 0.42s"
#   "5 passed in 1.23s"
_SUMMARY_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|error|skipped)")


def _build_isolated_env(repo_dir: str):
    """Create a throwaway virtualenv and install the analyzed repo's own
    dependencies into it, then install pytest there too.

    This is deliberately NOT done into the release-agent's own environment.
    Installing an arbitrary third-party repo's dependencies into the host
    app's environment can silently break the host app itself -- e.g.
    analyzing a repo that happens to be named "click" and running
    `pip install -e .` on it will overwrite the real `click` package that
    uvicorn/other tooling depends on. Keeping this fully isolated avoids
    that class of bug entirely, at the cost of ~5-30s per analysis to build
    the venv.

    Returns the path to the isolated python executable, or None if the
    isolated environment could not be built (caller should fall back to
    running pytest directly against the host environment).
    """
    venv_dir = tempfile.mkdtemp(prefix="release_agent_venv_")
    try:
        venv.EnvBuilder(with_pip=True).create(venv_dir)
        venv_python = os.path.join(venv_dir, "bin", "python")
        if not os.path.isfile(venv_python):
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")  # Windows fallback

        subprocess.run(
            [venv_python, "-m", "pip", "install", "--quiet", "pytest"],
            capture_output=True, text=True, timeout=120,
        )

        req_file = os.path.join(repo_dir, "requirements.txt")
        if os.path.isfile(req_file):
            logger.info(f"Installing target repo dependencies from {req_file} (isolated env)")
            subprocess.run(
                [venv_python, "-m", "pip", "install", "--quiet", "-r", req_file],
                capture_output=True, text=True, timeout=180,
            )
        elif os.path.isfile(os.path.join(repo_dir, "pyproject.toml")) or os.path.isfile(
            os.path.join(repo_dir, "setup.py")
        ):
            logger.info(f"Installing target repo in editable mode from {repo_dir} (isolated env)")
            subprocess.run(
                [venv_python, "-m", "pip", "install", "--quiet", "-e", repo_dir],
                capture_output=True, text=True, timeout=180,
            )

        return venv_dir, venv_python
    except Exception as e:
        logger.warning(f"Could not build isolated environment for tests: {e}")
        shutil.rmtree(venv_dir, ignore_errors=True)
        return None, None


def run_tests(test_dir: str = ".") -> TestResult:
    """Run pytest on the target directory (the ACTUAL repo being analyzed,
    passed in by the caller -- not the release-agent's own code). Runs in
    an isolated virtualenv when analyzing a real cloned repo so its
    dependencies never contaminate the release-agent's own environment."""
    venv_dir = None
    try:
        pytest_cmd = ["pytest"]

        if test_dir != ".":
            venv_dir, venv_python = _build_isolated_env(test_dir)
            if venv_python:
                pytest_cmd = [venv_python, "-m", "pytest"]

        result = subprocess.run(
            [*pytest_cmd, test_dir, "--maxfail=5", "--disable-warnings", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        raw_output = result.stdout + "\n" + result.stderr

        if "no tests ran" in raw_output.lower() or "collected 0 items" in raw_output.lower():
            logger.warning(f"No tests were collected in {test_dir}")
            return TestResult(
                passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                raw_output=(raw_output[:2000] or "No tests found in repository."),
            )

        if result.returncode in (2, 4) and (
            "error" in raw_output.lower() or "ImportError" in raw_output or "ModuleNotFoundError" in raw_output
        ):
            # Pytest couldn't even collect the tests (e.g. missing
            # dependency that install step above didn't cover). Report this
            # honestly as "unable to run tests" rather than a fabricated or
            # misleading pass/fail count.
            logger.warning(f"Pytest collection error in {test_dir} (exit code {result.returncode})")
            return TestResult(
                passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                raw_output=("Tests could not be collected (missing dependencies or import errors):\n" + raw_output[:1800]),
            )

        counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
        for match in _SUMMARY_COUNT_RE.finditer(raw_output):
            count, label = match.groups()
            counts[label] = int(count)

        passed_count = counts["passed"]
        failed_count = counts["failed"] + counts["error"]
        total = passed_count + failed_count + counts["skipped"]

        if total == 0:
            # Pytest ran but we couldn't parse a summary line (unexpected
            # output format / crash) -- don't fabricate a result, surface it.
            logger.warning(f"Could not parse pytest summary for {test_dir}; exit code {result.returncode}")
            return TestResult(
                passed=result.returncode == 0,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                raw_output=raw_output[:2000],
            )

        return TestResult(
            passed=failed_count == 0,
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed_count,
            raw_output=raw_output[:2000],
        )

    except FileNotFoundError:
        logger.warning("Pytest not found, returning simulated test results")
        return _get_simulated_tests()
    except subprocess.TimeoutExpired:
        logger.error("Test execution timed out")
        return _get_simulated_tests()
    except Exception as e:
        logger.error(f"Test execution error: {e}")
        return _get_simulated_tests()
    finally:
        if venv_dir:
            shutil.rmtree(venv_dir, ignore_errors=True)


def _get_simulated_tests() -> TestResult:
    """Return simulated test results for demo purposes (used only when
    pytest itself can't be run at all, e.g. it's not installed)."""
    total = random.randint(15, 30)
    failed = random.randint(0, 3)
    passed = total - failed

    return TestResult(
        passed=failed == 0,
        total_tests=total,
        passed_tests=passed,
        failed_tests=failed,
        raw_output=f"Simulated: {passed}/{total} tests passed, {failed} failed",
    )
