import hashlib
import hmac
from django.conf import settings


def get_tracker_secret_key() -> str:
    """Retrieve the configured HMAC secret key for Intelligent Tracker edge nodes."""
    return getattr(
        settings,
        "INTELLIGENT_TRACKER_SECRET_KEY",
        "default-dev-tracker-secret-key-change-in-prod",
    )


def calculate_hmac_signature(payload_bytes: bytes, secret: str = None) -> str:
    """
    Computes an HMAC-SHA256 hexadecimal digest for the given payload bytes.
    """
    if secret is None:
        secret = get_tracker_secret_key()
    key = secret.encode("utf-8")
    return hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()


def verify_hmac_signature(payload_bytes: bytes, signature_header: str, secret: str = None) -> bool:
    """
    Validates the X-Tracker-Signature header against the calculated HMAC-SHA256.
    Supports both raw hexadecimal digest and 'sha256=<hex>' format.
    Uses constant-time comparison to protect against timing attacks.
    """
    if not signature_header:
        return False

    if secret is None:
        secret = get_tracker_secret_key()

    if not secret:
        return False

    received_sig = signature_header.strip()
    if received_sig.lower().startswith("sha256="):
        received_sig = received_sig[7:].strip()

    expected_sig = calculate_hmac_signature(payload_bytes, secret)
    return hmac.compare_digest(expected_sig.lower(), received_sig.lower())


def get_client_ip(request) -> str:
    """Extracts client IP address safely considering reverse proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
