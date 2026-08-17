import hmac
import hashlib
from typing import Optional


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

    Returns True (verification "passes") when no secret is configured at
    all -- this keeps local/demo use working without forcing webhook setup,
    but callers should log a clear warning whenever they rely on this path,
    since it means signatures aren't actually being checked.
    """
    if not secret:
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)
