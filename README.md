# 🤖 Autonomous Software Release Agent

> An AI-powered DevOps release decision engine that analyzes code changes, runs automated tests and security scans, and makes intelligent, auditable release decisions — with zero manual gatekeeping required.

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Tests](https://img.shields.io/badge/tests-64%20passing-brightgreen)](./tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## Overview

Shipping software safely usually means someone manually reviewing test results, security scans, and diff risk before clicking "approve." This project automates that judgment call.

The **Autonomous Software Release Agent** listens for GitHub push/PR events, pulls the relevant diff, runs your test suite, performs static security analysis, and feeds the results into an AI (or rule-based) decision engine that returns a clear **approve / hold / reject** verdict — complete with reasoning, risk score, and a full audit trail — surfaced on a live React dashboard.

## Why this exists

- **Removes bottlenecks** — routine, low-risk changes get auto-approved instead of waiting on a human reviewer.
- **Catches what humans miss** — combines static security scanning (Bandit) with LLM-based reasoning over the actual diff.
- **Auditable by design** — every decision is logged with its inputs, score, and rationale for compliance and postmortems.
- **Works without API keys** — ships with a rule-based fallback decision engine, so it runs in demo mode out of the box.

## Architecture

```
GitHub Repo → GitHub Webhook (HMAC-verified) → FastAPI Backend
                                                     │
                                    ┌────────────────┼────────────────┐
                                    ▼                ▼                ▼
                            Run Tests (pytest)  Security Scan    AI Decision Engine
                                                   (Bandit)      (Groq LLM / Rule-based)
                                    │                │                │
                                    └──────────────┴────────────────┘
                                                     ▼
                                          Decision JSON (risk score,
                                          verdict, reasoning)
                                                     ▼
                                          React Dashboard (live)
```

## Key Features

| Area | Capability |
|---|---|
| 🔗 **GitHub Integration** | Verified webhook ingestion (HMAC-SHA256) for push/PR events, plus manual trigger endpoint |
| 🧪 **Automated Testing** | Runs the target repo's `pytest` suite and parses pass/fail results |
| 🛡️ **Security Scanning** | Static analysis via Bandit, categorized by vulnerability severity |
| 🧠 **AI Decision Engine** | LLM-based release reasoning (Groq) with a deterministic rule-based fallback — no API key required |
| 📊 **Live Dashboard** | Real-time approve/hold/reject status, animated risk gauge, security breakdown, and test summary |
| 📋 **Audit Trail** | Full, queryable history of every release decision ever made |
| ⚙️ **Background Jobs** | Async job processing so webhook responses stay fast even on large repos |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | React 18 + Vite |
| AI Engine | Groq (Llama 3.3 70B) with rule-based fallback |
| Security Scanning | Bandit |
| Testing | Pytest (64-test backend suite) |
| Styling | Custom dark-themed CSS + 3D risk gauge |
| Deployment | Docker |

## Dashboard Preview

- ✅ **Release Status Indicator** — real-time approve / reject / hold verdicts
- 📊 **Risk Meter** — animated SVG/3D arc gauge with color-coded risk scoring
- 🛡️ **Security Chart** — vulnerability severity breakdown at a glance
- 🧪 **Test Summary** — donut chart of pass/fail results
- 📋 **Decision History** — full audit trail of every release evaluated

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+

### Backend Setup

```bash
cd release-agent
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd release-agent/frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
OPENAI_API_KEY=your_groq_api_key    # Optional — Groq key, works without one (demo mode)
GITHUB_TOKEN=your_github_token      # Optional — required for private repo access
GITHUB_REPO=owner/repo              # Optional — target repo for analysis
WEBHOOK_SECRET=your_webhook_secret  # Optional — verifies GitHub webhook signatures
SECRET_KEY=your_secret_key          # App secret key
```

> **Note:** The application works fully in demo mode without any API keys, using the rule-based decision engine.

### Run with Docker

```bash
docker build -t release-agent .
docker run -p 8000:8000 --env-file .env release-agent
```

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/webhook/github` | GitHub webhook handler (HMAC-verified) |
| `POST` | `/webhook/analyze` | Manually trigger analysis for a repo/commit |
| `GET` | `/webhook/history` | Full decision history |
| `GET` | `/webhook/stats` | Aggregate dashboard statistics |
| `GET` | `/api/health` | Health check |

## Project Structure

```
release-agent/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Environment-based configuration
│   ├── models.py                # Pydantic models
│   ├── services/
│   │   ├── github_service.py    # GitHub API integration
│   │   ├── test_service.py      # Test execution (pytest)
│   │   ├── security_service.py  # Security scanning (Bandit)
│   │   ├── ai_service.py        # AI evaluation (Groq)
│   │   ├── decision_engine.py   # Orchestration & verdict logic
│   │   └── job_store.py         # Async background job tracking
│   ├── routes/
│   │   └── webhook.py           # API routes
│   └── utils/
│       └── logger.py            # Logging utility
├── frontend/
│   ├── src/
│   │   ├── components/          # Dashboard, RiskGauge3D, etc.
│   │   ├── services/api.js      # API client
│   │   ├── App.jsx / main.jsx
│   │   └── index.css            # Design system
│   ├── vite.config.js
│   └── package.json
├── tests/                       # 64-test pytest suite
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## Testing

```bash
pytest tests/ -v
```

The backend ships with a 64-test suite covering webhook security (HMAC verification), the decision engine, GitHub integration, AI service, security scanning, and job storage.

## Roadmap

- [ ] Multi-repo dashboard view
- [ ] Slack/Discord release notifications
- [ ] Pluggable decision policies (org-defined approval thresholds)
- [ ] Support for additional CI providers (GitLab CI, CircleCI)

## Contributing

Contributions, issues, and feature requests are welcome. Feel free to open an issue or submit a PR.

## License

MIT
