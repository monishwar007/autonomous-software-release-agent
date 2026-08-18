# 🚀 How to Run — Autonomous Software Release Agent

> AI-Powered DevOps Release Decision Engine for Intelligent Release Governance

---

## 📋 Prerequisites

| Tool    | Version | Download                                          |
|---------|---------|---------------------------------------------------|
| Python  | 3.9+    | [python.org/downloads](https://python.org/downloads) |
| Node.js | 18+     | [nodejs.org](https://nodejs.org)                  |
| pip     | latest  | Comes with Python                                 |
| Git     | any     | [git-scm.com](https://git-scm.com)               |

**Verify installations:**

```bash
python --version     # Should show Python 3.9+
node --version       # Should show v18+
npm --version        # Should show 9+
pip --version        # Should show pip 21+
```

---

## 📁 Project Structure

```
release-agent/
├── app/                         # FastAPI Backend (Python)
│   ├── main.py                  # Application entry point
│   ├── config.py                # Environment configuration
│   ├── models.py                # Pydantic data models
│   ├── services/                # Core business logic
│   │   ├── ai_service.py        # AI evaluation (Groq LLM)
│   │   ├── decision_engine.py   # Release decision orchestrator
│   │   ├── github_service.py    # GitHub API integration
│   │   ├── security_service.py  # Security scanning (Bandit)
│   │   └── test_service.py      # Test execution (pytest)
│   ├── routes/
│   │   └── webhook.py           # API endpoints
│   └── utils/
│       └── logger.py            # Logging utility
├── frontend/                    # React 18 Dashboard (Vite)
│   ├── src/
│   │   ├── components/          # Dashboard, Charts, Cards
│   │   ├── services/api.js      # API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker containerization
├── .env                         # Environment variables
└── README.md
```

---

## ⚙️ Step 1 — Configure Environment Variables

A `.env` file should exist in the `release-agent/` root directory. If not, create one:

```env
# AI Configuration (Optional — app works in demo mode without this)
OPENAI_API_KEY=your_groq_api_key_here       # Groq key (starts with gsk_...)
GROQ_MODEL=llama-3.3-70b-versatile          # LLM model to use

# GitHub Configuration (Optional)
GITHUB_TOKEN=your_github_token_here
GITHUB_REPO=owner/repo_name

# Security
SECRET_KEY=your_secret_key_here
```

> **💡 Note:** The application runs in **demo mode** without any API keys.
> Without a Groq key, the system uses a built-in **rule-based evaluation** engine for release decisions.

### How to Get API Keys (Optional)

| Key            | Where to Get It                                                     |
|----------------|---------------------------------------------------------------------|
| Groq API Key   | Sign up at [console.groq.com](https://console.groq.com) → API Keys |
| GitHub Token   | GitHub → Settings → Developer Settings → Personal Access Tokens     |

---

## ⚙️ Step 2 — Install & Start the Backend

Open a terminal in the `release-agent/` directory:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn app.main:app --reload --port 8000
```

**Expected output:**

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Verify the backend is running:**

| URL                                  | Purpose            |
|--------------------------------------|--------------------|
| http://localhost:8000/api/health      | Health check       |
| http://localhost:8000/docs            | Swagger API docs   |

> ⚠️ **Keep this terminal open.** Open a **new terminal** for the frontend.

---

## ⚙️ Step 3 — Install & Start the Frontend

Open a **second terminal** and navigate to the `frontend/` directory:

```bash
cd frontend

# Install Node.js dependencies
npm install

# Start the Vite dev server
npm run dev
```

**Expected output:**

```
VITE v5.x.x  ready in XXX ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

> The Vite dev server automatically proxies `/webhook/*` and `/api/*` requests to the backend at `http://localhost:8000`.

---

## ✅ Step 4 — Use the Application

Open **http://localhost:3000** in your browser. The Release Agent Dashboard includes:

| Feature              | Description                                    |
|----------------------|------------------------------------------------|
| 🟢 Release Status    | Real-time approve / reject / hold decisions    |
| 📊 Risk Meter        | SVG arc gauge with color-coded risk scoring    |
| 🛡️ Security Chart    | Vulnerability severity breakdown               |
| 🧪 Test Summary      | Donut chart with pass/fail analysis            |
| 📋 Decision History  | Full audit trail of all past releases          |

### Triggering an Analysis

**Option A — Dashboard UI**
Click the **"Run Analysis"** button on the dashboard.

**Option B — cURL / Postman**

```bash
curl -X POST http://localhost:8000/webhook/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "owner/repo",
    "branch": "main",
    "commit_id": ""
  }'
```

**Option C — Swagger UI**
1. Open http://localhost:8000/docs
2. Find **POST /webhook/analyze**
3. Click **"Try it out"** → fill in the body → **"Execute"**

---

## 🔌 API Endpoints

| Method | Endpoint                    | Description                                              |
|--------|-----------------------------|------------------------------------------------------------|
| GET    | `/api/health`               | Health check                                              |
| POST   | `/webhook/github`           | GitHub webhook handler (automatic, HMAC-signed)           |
| POST   | `/webhook/analyze`          | Manually trigger release analysis, returns a `job_id`     |
| GET    | `/webhook/analyze/{job_id}` | Poll status/result of a background analysis job           |
| GET    | `/webhook/history`          | Retrieve past release decisions                           |
| GET    | `/webhook/stats`            | Dashboard summary statistics                               |

**Analysis is asynchronous.** `POST /webhook/analyze` returns immediately
with a `job_id` (a full analysis — clone + isolated venv + dependency
install + pytest + bandit — can take anywhere from a few seconds to a
couple of minutes). Poll `GET /webhook/analyze/{job_id}` until `status` is
`completed` or `failed`. The dashboard frontend already does this polling
for you; you only need to think about it if you're calling the API directly.

---

## 🔗 Setting up the real GitHub webhook

This turns the agent from something you have to query into something that
runs automatically on every push and posts its decision back to GitHub as
a commit status check (which can gate merges via branch protection rules).

1. Generate a random secret, e.g. `openssl rand -hex 20`, and set it as
   `WEBHOOK_SECRET` in your `.env`.
2. In your target GitHub repo: **Settings → Webhooks → Add webhook**
   - Payload URL: `https://<your-deployed-host>/webhook/github`
   - Content type: `application/json`
   - Secret: the same value as `WEBHOOK_SECRET`
   - Events: select just **"Pushes"** (the agent currently only acts on `push`)
3. Make sure `GITHUB_TOKEN` has permission to write commit statuses
   (classic PAT with `repo:status` scope, or a fine-grained token with
   "Commit statuses: write") — this is what lets the agent post its
   `approve`/`reject`/`hold` decision back onto the commit.
4. Push a commit. GitHub will POST to `/webhook/github`; the agent
   verifies the signature, queues a background analysis job, and — once
   it finishes — posts a status check on that commit.

Without `WEBHOOK_SECRET` set, this endpoint still works (useful for local
testing with a tool like `ngrok`), but signature verification is disabled
and a warning is logged on every request — don't deploy it publicly like that.

---

## ✅ Running the backend's own test suite

The release-agent has its own pytest suite covering the services above
(commit fetching/cloning, test/security scan parsing, the rule-based risk
scorer, the async job store, and the webhook routes themselves — including
signature verification):

```bash
cd release-agent
pip install -r requirements.txt
pytest tests/ -v
```

All tests run against mocked subprocess/network calls, so this is fast
(well under a second) and doesn't require git, bandit, or network access.

---

## 🐳 Running with Docker (Alternative)

```bash
# Build the image
docker build -t release-agent .

# Run the container
docker run -p 8000:8000 --env-file .env release-agent
```

> **Note:** Docker runs only the backend. For the full dashboard experience, use the manual setup above.

---

## 🛠️ Troubleshooting

| Problem                          | Solution                                                      |
|----------------------------------|---------------------------------------------------------------|
| `pip` not found                  | Use `pip3` instead, or add Python to PATH                     |
| `npm` not found                  | Reinstall Node.js from [nodejs.org](https://nodejs.org)       |
| Port 8000 already in use        | Use `--port 8001` in the uvicorn command                      |
| Port 3000 already in use        | Vite will auto-pick the next available port                   |
| CORS errors in browser          | Ensure the backend is running on port 8000                    |
| "Groq not available" warning    | Normal — the app falls back to rule-based evaluation          |
| Frontend shows no data          | Trigger an analysis first (Step 4)                            |
| `ModuleNotFoundError`           | Re-run `pip install -r requirements.txt`                      |

---

## ⚡ Quick Start (TL;DR)

```bash
# Terminal 1 — Backend
cd release-agent
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd release-agent/frontend
npm install
npm run dev
```

Then open **http://localhost:3000** in your browser. 🎉
