import os
import shutil
import subprocess
import tempfile
import requests
from app.config import GITHUB_TOKEN, GITHUB_REPO
from app.utils.logger import logger
from app.models import CommitData
from typing import Optional


def _fetch_commit(target_repo: str, branch: str, headers: dict) -> Optional[CommitData]:
    """Low-level helper: call the GitHub API once with the given headers."""
    url = f"https://api.github.com/repos/{target_repo}/commits/{branch}"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    commit = data.get("commit", {})
    files = data.get("files", [])

    return CommitData(
        commit_id=data.get("sha", "")[:8],
        author=commit.get("author", {}).get("name", "Unknown"),
        message=commit.get("message", ""),
        timestamp=commit.get("author", {}).get("date", ""),
        files_changed=[f.get("filename", "") for f in files],
        additions=sum(f.get("additions", 0) for f in files),
        deletions=sum(f.get("deletions", 0) for f in files),
    )


def get_latest_commit(repo: str = "", branch: str = "main") -> Optional[CommitData]:
    """Fetch the latest commit from a GitHub repository.

    Behavior:
    - If no repo is specified at all (pure demo mode), return mock data.
    - If a repo IS specified, always try a real API call first. If a
      configured GITHUB_TOKEN is invalid/expired (401/403), retry once
      without auth (works fine for public repos) before giving up.
    - Only fall back to mock data if the repo truly can't be reached, and
      make that failure visible in the returned commit message instead of
      silently pretending it was a real (and always-identical) commit.
    """
    target_repo = repo or GITHUB_REPO
    if not target_repo:
        logger.warning("No GitHub repo configured, returning mock data (demo mode)")
        return _get_mock_commit()

    # Attempt 1: with configured token, if any
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        return _fetch_commit(target_repo, branch, headers)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if headers and status in (401, 403):
            logger.warning(
                f"GITHUB_TOKEN rejected ({status}) for {target_repo}, "
                f"retrying unauthenticated (works for public repos)"
            )
            try:
                return _fetch_commit(target_repo, branch, headers={})
            except Exception as e2:
                logger.error(f"GitHub API error for {target_repo} (unauthenticated retry): {e2}")
        else:
            logger.error(f"GitHub API error for {target_repo}: {e}")
    except Exception as e:
        logger.error(f"GitHub API error for {target_repo}: {e}")

    return _get_unreachable_commit(target_repo)


def clone_repository(repo: str, branch: str = "main") -> Optional[str]:
    """Shallow-clone the target repo into a temp directory so tests/security
    scans run against the ACTUAL analyzed repo instead of the agent's own
    codebase. Returns the local path, or None if cloning wasn't possible.

    Caller is responsible for calling cleanup_repository() when done.
    """
    if not repo:
        return None

    if shutil.which("git") is None:
        logger.warning("git executable not found, cannot clone repo for real analysis")
        return None

    tmp_dir = tempfile.mkdtemp(prefix="release_agent_")

    # Use token in the URL if available (needed for private repos); fall back
    # to the plain public URL if that fails.
    urls_to_try = []
    if GITHUB_TOKEN:
        urls_to_try.append(f"https://{GITHUB_TOKEN}@github.com/{repo}.git")
    urls_to_try.append(f"https://github.com/{repo}.git")

    for url in urls_to_try:
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, url, tmp_dir],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                logger.info(f"Cloned {repo}@{branch} to {tmp_dir}")
                return tmp_dir
            logger.warning(f"git clone failed for {repo}@{branch}: {result.stderr.strip()[:300]}")
        except subprocess.TimeoutExpired:
            logger.error(f"git clone timed out for {repo}")
            break
        except Exception as e:
            logger.error(f"git clone error for {repo}: {e}")
            break

    # Clean up the empty/partial dir if clone never succeeded
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return None


def cleanup_repository(path: Optional[str]) -> None:
    """Remove a temp directory created by clone_repository()."""
    if path and os.path.isdir(path) and path.startswith(tempfile.gettempdir()):
        shutil.rmtree(path, ignore_errors=True)


def post_commit_status(
    repo: str,
    sha: str,
    state: str,
    description: str = "",
    context: str = "release-agent/analysis",
) -> bool:
    """Post a commit status check back to GitHub so the agent's decision is
    visible directly on the commit/PR (and can gate merging via branch
    protection rules) instead of only being queryable through this API.

    `state` must be one of GitHub's four supported values:
    "error", "failure", "pending", "success".

    Requires GITHUB_TOKEN to have write access to commit statuses (the
    classic "repo:status" scope, or "Commit statuses: write" on a
    fine-grained token).
    """
    if not GITHUB_TOKEN:
        logger.warning(f"No GITHUB_TOKEN configured, cannot post status for {repo}@{sha}")
        return False

    if not repo or not sha:
        logger.warning("post_commit_status called without repo/sha, skipping")
        return False

    url = f"https://api.github.com/repos/{repo}/statuses/{sha}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    payload = {
        "state": state,
        # GitHub silently truncates long descriptions; keep it well under
        # the ~140 char limit so nothing important gets cut off.
        "description": description[:140],
        "context": context,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Posted status '{state}' to {repo}@{sha[:8]}")
        return True
    except Exception as e:
        logger.error(f"Failed to post commit status to {repo}@{sha[:8]}: {e}")
        return False


def _get_mock_commit() -> CommitData:
    """Return mock commit data for demo/testing (no repo configured at all)."""
    from datetime import datetime
    return CommitData(
        commit_id="a1b2c3d4",
        author="DevOps Agent",
        message="feat: update authentication module with new security patches",
        timestamp=datetime.now().isoformat(),
        files_changed=[
            "src/auth/login.py",
            "src/auth/middleware.py",
            "src/utils/validators.py",
            "tests/test_auth.py",
        ],
        additions=142,
        deletions=38,
    )


def _get_unreachable_commit(target_repo: str) -> CommitData:
    """Return a clearly-labeled placeholder when a SPECIFIC repo was
    requested but could not be reached. Deliberately has no files_changed
    so it doesn't spuriously trigger risk heuristics (e.g. 'auth' keyword
    matches) for a commit that was never actually fetched.
    """
    from datetime import datetime
    return CommitData(
        commit_id="unknown",
        author="unknown",
        message=(
            f"Could not fetch commit data for '{target_repo}'. "
            f"Check that the repo name/branch is correct and, if private, "
            f"that GITHUB_TOKEN is valid."
        ),
        timestamp=datetime.now().isoformat(),
        files_changed=[],
        additions=0,
        deletions=0,
    )
