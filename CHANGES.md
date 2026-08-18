# Bug Fixes — Release Readiness Analysis

## The reported problem
Analyzing any GitHub repo always returned a risk score around 20%,
regardless of the repo.

## Root cause
The analyzer was never actually analyzing the target repo. Three bugs compounded:

1. **`app/services/github_service.py`** — the `GITHUB_TOKEN` in `.env` was
   expired/invalid. Every real API call returned `401 Unauthorized`, which
   silently fell back to a **hardcoded mock commit** (same fake commit,
   same fake files, every time) — regardless of what repo was requested.

2. **`app/services/decision_engine.py`** — `run_tests()` and
   `run_security_scan()` were called with no directory argument, so they
   defaulted to `"."` — wherever the FastAPI server process happened to be
   running (the release-agent's *own* code), never the repo being analyzed.

3. **`app/services/test_service.py`** — when pytest collected 0 real tests,
   the code fabricated a fake "12/12 passed" result instead of reporting
   that no tests were found.

Combined, every analysis fed the risk scorer the same fixed inputs, so it
converged on the same ~0.18–0.20 score no matter which repo was submitted.

## Fixes applied

| File | Fix |
|---|---|
| `github_service.py` | Retries unauthenticated on 401/403 (works for public repos even with a dead token). Added `clone_repository()` to shallow-clone the actual target repo. Failures to fetch a *specific* requested repo now return a clearly-labeled "unreachable" result instead of a fake commit. |
| `test_service.py` | Removed fabricated pass counts. Added regex-based pytest summary parsing. Runs tests inside a disposable, isolated virtualenv (see below) with best-effort dependency installation so real repos' tests can actually import their own code. |
| `security_service.py` | Fixed a bug reading bandit's summary (code looked for a `_summary` key that doesn't exist; bandit calls it `_totals`), which made `scanned_files` always fall back to a hardcoded value. Also fixed JSON parsing — newer bandit versions print a progress bar before the JSON, which broke `json.loads()` silently. |
| `ai_service.py` | Fixed a `NameError` crash in the empty-AI-response fallback path (referenced undefined variable names). |
| `decision_engine.py` | Wires the real clone path through to tests/security scans, with `try/finally` cleanup. |
| `Dockerfile` | Added `git` (required for cloning at runtime; wasn't in the base image). |
| `.gitignore`, `.env.example` (new) | `.env` contained a real-looking GitHub PAT and Groq API key. Added `.gitignore` so it's never committed, and a safe `.env.example` template. **Recommend rotating both keys before pushing this project anywhere.** |

## Important design note: isolated virtualenv per analysis
Installing an arbitrary analyzed repo's dependencies into the *same*
environment as the running release-agent is dangerous — e.g. analyzing a
repo that happens to be named `click` and running `pip install -e .` on it
will silently overwrite the real `click` package your own server depends
on (this actually happened during testing and broke the server). Test
execution now happens inside a disposable virtualenv built per-analysis
and torn down afterward, so the analyzed repo's dependencies can never
collide with the release-agent's own runtime.

## Verified behavior after the fix
Live-tested against `pallets/click` and `pallets/flask`:
- Real, different commit data per repo
- Real pytest results per repo (e.g. 1723/1752 passed, 5 failed on click)
- Real bandit security findings per repo (different file counts, severities)
- Risk scores now vary meaningfully (0.0–0.5+ depending on real findings)
  instead of clustering at ~20%
- Demo mode (no repo configured) still works as a graceful fallback
- Frontend builds cleanly after a clean `node_modules` reinstall (the
  bundled `node_modules` in the original zip had a corrupted
  platform-specific `rollup` binary — a known npm optional-dependency bug;
  run `npm install` fresh if you hit `Cannot find module
  @rollup/rollup-linux-x64-gnu`)

## Before you demo/submit
1. Rotate the GitHub PAT and Groq API key currently in `.env` (they're
   real credentials that were exposed in the uploaded project).
2. Run `npm install` fresh in `frontend/` (node_modules wasn't shipped in
   this fixed copy — see below).
3. `pip install -r requirements.txt` for the backend, then
   `uvicorn app.main:app --reload` per `HOW_TO_RUN.md`.

---

# Round 2 — Autonomy, test coverage, and non-blocking analysis

## 1. Real autonomous webhook (was: manual-only)

Previously `/webhook/github` was a stub — it accepted whatever payload was
posted with no verification and returned the full analysis synchronously.
Now:

- **HMAC-SHA256 signature verification** (`app/utils/webhook_security.py`)
  against `X-Hub-Signature-256`, using `hmac.compare_digest` to avoid
  timing attacks. Configured via the new `WEBHOOK_SECRET` env var. Without
  it, the endpoint still works (for local testing) but logs a clear
  warning on every request.
- **Event filtering**: `ping` is acknowledged without triggering analysis;
  only `push` events are acted on; anything else is acknowledged and
  ignored (not errored — GitHub retries non-2xx responses).
- **Posts the decision back to GitHub** as a commit status check
  (`github_service.post_commit_status`) on the exact commit SHA from the
  webhook payload, so the result is visible directly on GitHub and can
  gate merges via branch protection. `approve` → `success`, `reject` →
  `failure`, `hold` → `failure` (GitHub's Statuses API has no native
  "needs review" state — see `job_store.DECISION_TO_GITHUB_STATE` if you
  want different behavior).
- See `HOW_TO_RUN.md` → "Setting up the real GitHub webhook" for setup steps.

## 2. Test suite for the release-agent itself (was: zero tests)

Added `tests/` with 64 tests covering every service module, run with
mocked subprocess/network calls (no git, bandit, or network needed —
full suite runs in well under a second):

- `test_webhook_security.py` — signature verification, including a
  tampered-payload test
- `test_test_service.py` — pytest output parsing, including regression
  tests for the "fabricated 12/12 passed" bug and the isolated-venv usage
- `test_security_service.py` — bandit output parsing, including
  regression tests for the progress-bar and `_summary`/`_totals` bugs
- `test_ai_service.py` — rule-based risk scoring logic, including a
  regression test for the empty-response `NameError` bug
- `test_github_service.py` — commit fetching (incl. the 401-retry logic),
  cloning, and a safety test that `cleanup_repository` can never `rmtree`
  outside the system temp dir
- `test_decision_engine.py` — orchestration: risk clamping, cleanup
  guarantees (even on failure), simulated-fallback behavior, history/stats
- `test_job_store.py` — async job lifecycle and decision→GitHub-state mapping
- `test_webhook_routes.py` — end-to-end route behavior via FastAPI's `TestClient`

Sanity-checked these aren't vacuous: temporarily reintroduced the original
`_summary`/`_totals` bug and confirmed 3 tests immediately fail, then
restored the fix and confirmed all 64 pass again.

Run with: `pytest tests/ -v`

## 4. Non-blocking analysis (was: request blocks for up to ~2 minutes)

`POST /webhook/analyze` and the GitHub webhook now return a `job_id`
immediately (`app/services/job_store.py`) instead of blocking until a full
clone+test+scan+AI-evaluation pipeline finishes. Analysis runs via
FastAPI's `BackgroundTasks` (which runs sync functions in a threadpool, so
the event loop isn't blocked); poll `GET /webhook/analyze/{job_id}` for
`pending` → `running` → `completed`/`failed`.

The frontend (`frontend/src/services/api.js`) was updated to poll
internally so `Dashboard.jsx` didn't need any changes — `triggerAnalysis()`
still resolves to the same shape it always did, just asynchronously
underneath.

Job state is in-memory (same tradeoff as `decision_history` — resets on
restart). A real deployment would back this with a database or a proper
task queue (Celery/RQ) so jobs survive restarts and can be distributed
across workers; in-memory is fine for this project's scope.
