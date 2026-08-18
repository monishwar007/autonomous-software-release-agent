import hmac
import hashlib

from app.utils.webhook_security import verify_github_signature


SECRET = "test-secret-123"
BODY = b'{"ref": "refs/heads/main"}'


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_no_secret_configured_always_passes():
    """Demo/local-dev mode: without a configured secret, verification is a
    no-op so the endpoint still works without forcing webhook setup."""
    assert verify_github_signature(BODY, None, secret="") is True
    assert verify_github_signature(BODY, "sha256=garbage", secret="") is True


def test_valid_signature_passes():
    signature = _sign(BODY, SECRET)
    assert verify_github_signature(BODY, signature, secret=SECRET) is True


def test_invalid_signature_fails():
    signature = _sign(BODY, "wrong-secret")
    assert verify_github_signature(BODY, signature, secret=SECRET) is False


def test_missing_signature_header_fails_when_secret_configured():
    assert verify_github_signature(BODY, None, secret=SECRET) is False
    assert verify_github_signature(BODY, "", secret=SECRET) is False


def test_malformed_signature_header_fails():
    """Header must be prefixed with 'sha256='; anything else (e.g. a bare
    hex digest, or a sha1= header from an old-style config) is rejected."""
    raw_digest = hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()
    assert verify_github_signature(BODY, raw_digest, secret=SECRET) is False
    assert verify_github_signature(BODY, f"sha1={raw_digest}", secret=SECRET) is False


def test_tampered_body_fails_signature_check():
    """Same signature, different body -- must fail (this is the actual
    attack HMAC verification defends against: a tampered payload)."""
    signature = _sign(BODY, SECRET)
    tampered_body = b'{"ref": "refs/heads/malicious-branch"}'
    assert verify_github_signature(tampered_body, signature, secret=SECRET) is False
