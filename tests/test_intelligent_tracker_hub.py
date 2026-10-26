import base64
import json
import uuid
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
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
    get_tracker_secret_key,
)
from intelligent_tracker_hub.plugin import IntelligentTrackerPlugin
from location_management.models import Countries, States, Cities, Location
from plugin_registry import registry

User = get_user_model()

# Valid 1x1 transparent PNG data in Base64
SAMPLE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(
        username="sec_operator",
        email="operator@example.com",
        password="ValidPassword123!",
        is_staff=True,
    )


@pytest.fixture
def test_location(db):
    country = Countries.objects.create(name="United States", code="US")
    state = States.objects.create(country=country, name="Texas", code="TX")
    city = Cities.objects.create(
        country=country,
        state=state,
        name="Austin",
        latitude=Decimal("30.2672"),
        longitude=Decimal("-97.7431"),
    )
    return Location.objects.create(
        name="North Production Campus",
        code="SITE-NORTH-01",
        city=city,
        address="1000 Industrial Parkway",
    )


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


# ==============================================================================
# 4. REST Catalog & Telemetry Stats API Tests
# ==============================================================================

@pytest.mark.django_db
def test_security_catalog_and_stats_api(client, test_location):
    e1 = SecurityEvent.objects.create(
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-01",
        severity=SecuritySeverity.HIGH,
    )
    e2 = SecurityEvent.objects.create(
        event_type=SecurityEventType.FALL_DETECTED,
        site=test_location,
        camera_id="cam-02",
        severity=SecuritySeverity.CRITICAL,
        is_resolved=True,
    )

    # Catalog API
    catalog_url = reverse("intelligent_tracker_api:security-events-catalog-list")
    resp_cat = client.get(catalog_url)
    assert resp_cat.status_code == 200
    cat_data = resp_cat.json()
    results = cat_data["results"] if "results" in cat_data else cat_data
    assert len(results) >= 2

    # Filtering by severity
    resp_filter = client.get(f"{catalog_url}?severity=CRITICAL")
    assert resp_filter.status_code == 200
    filter_data = resp_filter.json()
    filter_results = filter_data["results"] if "results" in filter_data else filter_data
    assert len(filter_results) == 1
    assert filter_results[0]["severity"] == "CRITICAL"

    # Stats API
    stats_url = reverse("intelligent_tracker_api:security_stats")
    resp_stats = client.get(stats_url)
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_events"] >= 2
    assert stats["unresolved_events"] >= 1
    assert "IntrusionAlert" in stats["events_by_type"]


# ==============================================================================
# 5. Web UI & Operations Dashboard Tests
# ==============================================================================

@pytest.mark.django_db
def test_dashboard_and_detail_views(client, auth_user, test_location):
    # Unauthenticated redirect
    dashboard_url = reverse("intelligent_tracker_hub:dashboard")
    resp = client.get(dashboard_url)
    assert resp.status_code == 302

    # Authenticated dashboard
    client.force_login(auth_user)
    event = SecurityEvent.objects.create(
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-east-perimeter",
        severity=SecuritySeverity.HIGH,
        metadata={"zone_name": "Fence Line East"},
    )

    resp_auth = client.get(dashboard_url)
    assert resp_auth.status_code == 200
    content = resp_auth.content.decode("utf-8")
    assert "Edge AI Spatial Security Hub" in content
    assert "cam-east-perimeter" in content
    assert "Fence Line East" in content

    # Event Detail View
    detail_url = reverse("intelligent_tracker_hub:event_detail", kwargs={"event_id": event.event_id})
    resp_detail = client.get(detail_url)
    assert resp_detail.status_code == 200
    assert "Evidence Snapshot" in resp_detail.content.decode("utf-8")

    # Resolve action
    resolve_url = reverse("intelligent_tracker_hub:event_resolve", kwargs={"event_id": event.event_id})
    resp_res = client.post(resolve_url, {"resolution_notes": "Operator resolved false positive."})
    assert resp_res.status_code == 302
    event.refresh_from_db()
    assert event.is_resolved is True
    assert event.resolved_by == auth_user

    # Mock dispatch simulation
    sim_url = reverse("intelligent_tracker_hub:simulate_dispatch")
    resp_sim = client.post(sim_url, {
        "event_type": "FallDetectedAlert",
        "camera_id": "cam-sim-01",
        "zone_name": "Loading Dock",
        "site_id": test_location.id,
    })
    assert resp_sim.status_code == 302
    assert SecurityEvent.objects.filter(camera_id="cam-sim-01").exists()

    # Webhook Audit View
    audit_url = reverse("intelligent_tracker_hub:audit_log")
    resp_audit = client.get(audit_url)
    assert resp_audit.status_code == 200
    assert "Edge AI Webhook Audit Trail" in resp_audit.content.decode("utf-8")


# ==============================================================================
# 6. Plugin Registry Discovery Test
# ==============================================================================

def test_intelligent_tracker_plugin_discovery():
    plugin = registry.get_plugin("intelligent_tracker_hub")
    assert plugin is not None
    assert plugin.name == "intelligent_tracker_hub"
    assert plugin.icon == "fa fa-shield"
    assert len(plugin.menu_items) == 1
    assert plugin.menu_items[0].url_name == "intelligent_tracker_hub:dashboard"
