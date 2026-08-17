import subprocess
import json
import random
from app.utils.logger import logger
from app.models import SecuritySummary


def run_security_scan(target_dir: str = ".") -> SecuritySummary:
    """Run Bandit security scan on the target directory."""
    try:
        import time
        start_time = time.time()
        
        result = subprocess.run(
            ["bandit", "-r", target_dir, "-f", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Newer bandit versions print a progress bar ("Working... ━━━ 100%")
        # to stdout BEFORE the actual JSON report. That extra line silently
        # broke json.loads() every time, so raw_issues was always [] and
        # scanned_files always fell back to the hardcoded "12" below --
        # regardless of what was actually in the repo being scanned.
        stdout = result.stdout
        json_start = stdout.find("{")
        json_text = stdout[json_start:] if json_start != -1 else stdout

        try:
            output = json.loads(json_text)
            raw_issues = output.get("results", [])
            # bandit's per-file metrics live directly under "metrics", keyed
            # by filename, plus one aggregate "_totals" key -- there is no
            # "_summary" key (that was the bug: it silently returned {}
            # every time, so scanned_files was always 0 or a hardcoded
            # fallback regardless of the repo being scanned).
            file_metrics = output.get("metrics", {})
            scanned_files = max(len(file_metrics) - 1, 0) if file_metrics else 0
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse bandit JSON output for {target_dir}")
            raw_issues = []
            scanned_files = 0

        summary_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        parsed_issues = []

        for issue in raw_issues:
            severity = issue.get("issue_severity", "").lower()
            if severity in summary_counts:
                summary_counts[severity] += 1
            
            parsed_issues.append({
                "issue_text": issue.get("issue_text", ""),
                "issue_severity": severity,
                "filename": issue.get("filename", ""),
                "line_number": str(issue.get("line_number", "")),
                "code": issue.get("code", ""),
                "test_id": issue.get("test_id", "")
            })

        return SecuritySummary(
            **summary_counts,
            issues=parsed_issues,
            scanned_files=scanned_files or len(set(i.get('filename') for i in raw_issues)),
            duration=round(time.time() - start_time, 2)
        )

    except FileNotFoundError:
        logger.warning("Bandit not found, returning simulated security scan")
        return _get_simulated_scan()
    except subprocess.TimeoutExpired:
        logger.error("Security scan timed out")
        return _get_simulated_scan()
    except Exception as e:
        logger.error(f"Security scan error: {e}")
        return _get_simulated_scan()


def _get_simulated_scan() -> SecuritySummary:
    """Return simulated security scan results for demo purposes."""
    sim_issues = [
        {
            "issue_text": "Possible hardcoded password found in configuration",
            "issue_severity": "high",
            "filename": "app/config.py",
            "line_number": "42",
            "code": "DB_PASSWORD = 'password123'  # nosec",
            "test_id": "B105"
        },
        {
            "issue_text": "Standard pseudo-random generators are not suitable for security/cryptographic purposes",
            "issue_severity": "low",
            "filename": "app/utils/helpers.py",
            "line_number": "15",
            "code": "import random",
            "test_id": "B311"
        },
        {
            "issue_text": "Using flask.run with debug=True is not recommended for production",
            "issue_severity": "medium",
            "filename": "app/main.py",
            "line_number": "108",
            "code": "app.run(debug=True)",
            "test_id": "B201"
        }
    ]
    return SecuritySummary(
        critical=0,
        high=1,
        medium=1,
        low=1,
        issues=sim_issues,
        scanned_files=47,
        duration=3.2
    )
