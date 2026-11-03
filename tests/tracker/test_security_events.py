import json
import uuid
import pytest
from django.urls import reverse
from django.utils import timezone

from intelligent_tracker_hub.models import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityAuditLog,
)
from intelligent_tracker_hub.security import (
    calculate_hmac_signature,
    verify_hmac_signature,
)
from .conftest import SAMPLE_PNG_BASE64
from .test_security_views import (
    test_security_catalog_and_stats_api,
    test_dashboard_and_detail_views,
    test_intelligent_tracker_plugin_discovery,
)

__all__ = [
    "test_calculate_and_verify_hmac_signature",
    "test_webhook_missing_hmac_returns_401",
    "test_webhook_invalid_hmac_returns_401",
    "test_webhook_valid_hmac_success",
    "test_webhook_with_base64_snapshot_and_site_code",
    "test_webhook_invalid_payload_returns_400",
    "test_security_event_model",
    "test_security_audit_log_model",
    "test_security_catalog_and_stats_api",
    "test_dashboard_and_detail_views",
    "test_intelligent_tracker_plugin_discovery",
]


# ==============================================================================
# 1. Security & Cryptographic HMAC Verification Tests
# ==============================================================================

def test_calculate_and_verify_hmac_signature():
    secret = "test-secret-key-12345"
    payload = b'{"camera_id": "cam-01", "event_type": "IntrusionAlert"}'

    sig = calculate_hmac_signature(payload, secret=secret)
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex is 64 chars

    # Valid verification with raw hex
    assert verify_hmac_signature(payload, sig, secret=secret) is True

    # Valid verification with 'sha256=' prefix
    assert verify_hmac_signature(payload, f"sha256={sig}", secret=secret) is True

    # Valid verification with uppercase prefix
    assert verify_hmac_signature(payload, f"SHA256={sig.upper()}", secret=secret) is True

    # Invalid signature
    assert verify_hmac_signature(payload, "invalid_hex_digest", secret=secret) is False

    # Tampered payload
    tampered = b'{"camera_id": "cam-01", "event_type": "TamperedAlert"}'
    assert verify_hmac_signature(tampered, sig, secret=secret) is False

    # Missing header or empty secret
    assert verify_hmac_signature(payload, "", secret=secret) is False
    assert verify_hmac_signature(payload, sig, secret="") is False


# ==============================================================================
# 2. Edge Webhook Receiver (POST /api/v1/security/events/) Tests
# ==============================================================================

@pytest.mark.django_db
def test_webhook_missing_hmac_returns_401(client):
    url = reverse("intelligent_tracker_api:security_event_webhook")
    payload = {"event_type": "IntrusionAlert", "camera_id": "cam-01"}

    resp = client.post(url, data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 401
    assert "detail" in resp.json()

    audit = SecurityAuditLog.objects.latest("id")
    assert audit.signature_valid is False
    assert audit.status_code == 401
    assert audit.processed_successfully is False


@pytest.mark.django_db
def test_webhook_invalid_hmac_returns_401(client):
    url = reverse("intelligent_tracker_api:security_event_webhook")
    payload = {"event_type": "IntrusionAlert", "camera_id": "cam-01"}

    resp = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE="deadbeef12345678",
    )
    assert resp.status_code == 401

    audit = SecurityAuditLog.objects.latest("id")
    assert audit.signature_valid is False
    assert audit.status_code == 401


@pytest.mark.django_db
def test_webhook_valid_hmac_success(client, test_location):
    url = reverse("intelligent_tracker_api:security_event_webhook")
    event_uuid = str(uuid.uuid4())
    payload = {
        "event_id": event_uuid,
        "event_type": "IntrusionAlert",
        "site_id": test_location.id,
        "camera_id": "cam-perimeter-north-01",
        "timestamp": timezone.now().isoformat(),
        "metadata": {
            "zone_name": "Restricted Outer Perimeter",
            "dwell_seconds": 18.5,
            "confidence": 0.94,
            "entity_id": "person_88",
        },
    }

    raw_body = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_body)

    resp = client.post(
        url,
        data=raw_body,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )

    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert res_data["event_id"] == event_uuid
    assert res_data["severity"] == SecuritySeverity.HIGH

    # Verify model persistence
    event = SecurityEvent.objects.get(event_id=event_uuid)
    assert event.event_type == SecurityEventType.INTRUSION
    assert event.camera_id == "cam-perimeter-north-01"
    assert event.site == test_location
    assert event.zone_name == "Restricted Outer Perimeter"
    assert event.dwell_seconds == 18.5
    assert event.confidence == 0.94
    assert event.entity_id == "person_88"
    assert event.is_resolved is False

    # Verify audit log
    audit = SecurityAuditLog.objects.latest("id")
    assert audit.signature_valid is True
    assert audit.status_code == 201
    assert audit.event_id == event_uuid
    assert audit.processed_successfully is True


@pytest.mark.django_db
def test_webhook_with_base64_snapshot_and_site_code(client, test_location):
    url = reverse("intelligent_tracker_api:security_event_webhook")
    event_uuid = str(uuid.uuid4())
    payload = {
        "event_id": event_uuid,
        "event_type": "FallDetectedAlert",
        "site_code": test_location.code,
        "camera_id": "cam-floor-02",
        "snapshot_base64": f"data:image/png;base64,{SAMPLE_PNG_BASE64}",
        "metadata": {"zone_name": "Warehouse Staging Area"},
    }

    raw_body = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_body)

    resp = client.post(
        url,
        data=raw_body,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=f"sha256={sig}",
    )

    assert resp.status_code == 201
    event = SecurityEvent.objects.get(event_id=event_uuid)
    assert event.severity == SecuritySeverity.CRITICAL
    assert event.site == test_location
    assert bool(event.snapshot) is True


@pytest.mark.django_db
def test_webhook_invalid_payload_returns_400(client):
    url = reverse("intelligent_tracker_api:security_event_webhook")
    # Missing camera_id and invalid event_type
    payload = {"event_type": "NonExistentEventType"}
    raw_body = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_body)

    resp = client.post(
        url,
        data=raw_body,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )

    assert resp.status_code == 400
    audit = SecurityAuditLog.objects.latest("id")
    assert audit.signature_valid is True
    assert audit.status_code == 400
    assert audit.processed_successfully is False


# ==============================================================================
# 3. Model Methods & Representation Tests
# ==============================================================================

@pytest.mark.django_db
def test_security_event_model(auth_user, test_location):
    event = SecurityEvent.objects.create(
        event_type=SecurityEventType.RESTRICTED_ENTITY,
        site=test_location,
        camera_id="cam-gate-03",
        severity=SecuritySeverity.CRITICAL,
        metadata={"zone_name": "Entry Gate", "confidence": 0.99, "dwell_seconds": 5},
    )

    assert str(event.event_id) in str(event)
    assert event.severity_badge_class == "danger"
    assert event.zone_name == "Entry Gate"
    assert event.dwell_seconds == 5
    assert event.confidence == 0.99

    # Resolution
    event.resolve(auth_user, notes="Security guard verified visitor clearance.")
    assert event.is_resolved is True
    assert event.resolved_by == auth_user
    assert event.resolved_at is not None
    assert "Security guard" in event.resolution_notes


@pytest.mark.django_db
def test_security_audit_log_model():
    log = SecurityAuditLog.objects.create(
        ip_address="192.168.1.50",
        endpoint="/api/v1/security/events/",
        status_code=201,
        processed_successfully=True,
    )
    assert "POST" in str(log)
    assert "OK" in str(log)
