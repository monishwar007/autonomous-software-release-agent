import os
from dotenv import load_dotenv

load_dotenv()

# AI Configuration - Supports both Groq and OpenAI
GROQ_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Groq key (gsk_...) stored in OPENAI_API_KEY
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

# GitHub webhook HMAC secret (must match the secret configured on the
# webhook in GitHub's repo settings). Used to verify that incoming
# /webhook/github requests genuinely came from GitHub.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# App Security
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
