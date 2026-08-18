import requests
from unittest.mock import patch, MagicMock

from app.services import github_service


def _http_error(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    err = requests.exceptions.HTTPError(response=resp)
    return err


def _fake_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


GITHUB_COMMIT_JSON = {
    "sha": "abcdef1234567890",
    "commit": {
        "author": {"name": "Jane Dev", "date": "2026-01-01T00:00:00Z"},
        "message": "fix: patch bug",
    },
    "files": [
        {"filename": "src/app.py", "additions": 10, "deletions": 2},
        {"filename": "src/utils.py", "additions": 3, "deletions": 1},
    ],
}


def test_no_repo_configured_returns_mock_commit():
    with patch.object(github_service, "GITHUB_REPO", ""):
        commit = github_service.get_latest_commit(repo="", branch="main")

    assert commit.commit_id == "a1b2c3d4"  # the documented demo-mode mock


def test_successful_fetch_parses_commit_correctly():
    with patch.object(github_service, "GITHUB_TOKEN", ""), \
         patch("app.services.github_service.requests.get", return_value=_fake_response(GITHUB_COMMIT_JSON)):
        commit = github_service.get_latest_commit(repo="octocat/Hello-World", branch="main")

    assert commit.commit_id == "abcdef12"
    assert commit.author == "Jane Dev"
    assert commit.additions == 13
    assert commit.deletions == 3
    assert "src/app.py" in commit.files_changed


def test_bad_token_retries_unauthenticated_and_succeeds():
    """Regression test: a dead/expired GITHUB_TOKEN used to cause every
    request for a specifically-named repo to silently fall back to fake
    mock data. It must now retry without auth (works for public repos)
    before giving up."""
    call_count = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        call_count["n"] += 1
        if headers and "Authorization" in headers:
            raise _http_error(401)
        return _fake_response(GITHUB_COMMIT_JSON)

    with patch.object(github_service, "GITHUB_TOKEN", "dead-token"), \
         patch("app.services.github_service.requests.get", side_effect=fake_get):
        commit = github_service.get_latest_commit(repo="octocat/Hello-World", branch="main")

    assert call_count["n"] == 2  # one failed authed attempt, one successful unauthed retry
    assert commit.commit_id == "abcdef12"


def test_totally_unreachable_repo_returns_labeled_placeholder_not_fake_data():
    """A specifically-requested repo that truly can't be reached must
    return a clearly-labeled failure, NOT the demo mock commit (which
    would silently look like a real, if fake, analysis)."""
    with patch.object(github_service, "GITHUB_TOKEN", ""), \
         patch("app.services.github_service.requests.get", side_effect=_http_error(404)):
        commit = github_service.get_latest_commit(repo="nonexistent/repo", branch="main")

    assert commit.commit_id == "unknown"
    assert commit.files_changed == []  # must not trigger risk heuristics for a fake commit
    assert "nonexistent/repo" in commit.message


def test_clone_repository_returns_none_when_git_missing():
    with patch("app.services.github_service.shutil.which", return_value=None):
        path = github_service.clone_repository("octocat/Hello-World", "main")
    assert path is None


def test_clone_repository_success():
    fake_result = MagicMock(returncode=0, stderr="")
    with patch("app.services.github_service.shutil.which", return_value="/usr/bin/git"), \
         patch("app.services.github_service.subprocess.run", return_value=fake_result), \
         patch("app.services.github_service.tempfile.mkdtemp", return_value="/tmp/release_agent_xyz"):
        path = github_service.clone_repository("octocat/Hello-World", "main")

    assert path == "/tmp/release_agent_xyz"


def test_clone_repository_failure_cleans_up_and_returns_none():
    fake_result = MagicMock(returncode=1, stderr="fatal: repo not found")
    with patch("app.services.github_service.shutil.which", return_value="/usr/bin/git"), \
         patch("app.services.github_service.subprocess.run", return_value=fake_result), \
         patch("app.services.github_service.tempfile.mkdtemp", return_value="/tmp/release_agent_xyz"), \
         patch("app.services.github_service.shutil.rmtree") as mock_rmtree:
        path = github_service.clone_repository("nonexistent/repo", "main")

    assert path is None
    mock_rmtree.assert_called()


def test_cleanup_repository_only_removes_temp_paths():
    """Safety check: cleanup_repository must refuse to rmtree anything
    outside the system temp directory, in case a bad path ever ends up
    there -- this must never be able to delete something like /etc."""
    with patch("app.services.github_service.shutil.rmtree") as mock_rmtree, \
         patch("app.services.github_service.os.path.isdir", return_value=True):
        github_service.cleanup_repository("/etc/important-stuff")
    mock_rmtree.assert_not_called()


def test_post_commit_status_without_token_does_not_call_api():
    with patch.object(github_service, "GITHUB_TOKEN", ""), \
         patch("app.services.github_service.requests.post") as mock_post:
        result = github_service.post_commit_status("owner/repo", "abc123", "success")

    assert result is False
    mock_post.assert_not_called()


def test_post_commit_status_success():
    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    with patch.object(github_service, "GITHUB_TOKEN", "valid-token"), \
         patch("app.services.github_service.requests.post", return_value=fake_resp) as mock_post:
        result = github_service.post_commit_status("owner/repo", "abc123", "success", "all good")

    assert result is True
    args, kwargs = mock_post.call_args
    assert "owner/repo/statuses/abc123" in args[0]
    assert kwargs["json"]["state"] == "success"


def test_post_commit_status_handles_api_failure_gracefully():
    with patch.object(github_service, "GITHUB_TOKEN", "valid-token"), \
         patch("app.services.github_service.requests.post", side_effect=Exception("network down")):
        result = github_service.post_commit_status("owner/repo", "abc123", "failure")

    assert result is False
