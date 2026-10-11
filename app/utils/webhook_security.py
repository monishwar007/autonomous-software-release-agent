import hmac
import hashlib
from typing import Optional

from app.config import ALLOW_UNSIGNED_WEBHOOKS


def verify_github_signature(payload_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """Verify GitHub's HMAC-SHA256 webhook signature.

    GitHub signs the raw request body with the shared webhook secret and
    sends the digest in the `X-Hub-Signature-256` header as
    `sha256=<hex digest>`. Without this check, anyone who discovers the
    webhook URL could POST an arbitrary payload and trigger an analysis (or
    a forged commit-status post-back) as if GitHub itself sent it.

    Uses hmac.compare_digest for the comparison to avoid leaking timing
    information that could help an attacker guess a valid signature
    byte-by-byte.

    FAILS CLOSED when no secret is configured: returns False unless the
    ALLOW_UNSIGNED_WEBHOOKS opt-in is enabled (local demo use only).
    Previously this returned True with no secret, which meant anyone who
    discovered the webhook URL could forge deliveries -- including forged
    push events that trigger expensive analysis jobs and commit-status
    post-backs made with the server's GitHub token.
    """
    if not secret:
        return ALLOW_UNSIGNED_WEBHOOKS

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)
