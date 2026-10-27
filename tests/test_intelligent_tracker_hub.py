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


# ==============================================================================
# 7. Milestone 16b (Phase E2) Video Evidence & Zero-Copy Stream Gateway Tests
# ==============================================================================

from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from video_gallery.models import VideoGallery, VideoItem


def test_video_evidence_zero_copy_register(client, test_location):
    """
    Validates zero-copy lightweight video evidence registration without disk bloat.
    """
    event = SecurityEvent.objects.create(
        event_id=uuid.uuid4(),
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-north-01",
        severity=SecuritySeverity.HIGH,
    )

    payload = {
        "event_id": str(event.event_id),
        "title": "Intrusion Sliced Clip - Cam North 01",
        "source_url": "http://192.168.1.150:8000/clips/intrusion_101.mp4",
        "site_code": test_location.code,
        "camera_id": "cam-north-01",
        "duration_seconds": 18.5,
        "thumbnail_base64": SAMPLE_PNG_BASE64,
        "trajectory": [
            {"x": 10.5, "y": 20.3, "t": 0.0},
            {"x": 12.0, "y": 22.4, "t": 1.5},
            {"x": 14.8, "y": 25.1, "t": 3.0},
        ],
        "metadata": {"zone": "Perimeter North", "confidence": 0.96},
    }
    raw_json = json.dumps(payload).encode("utf-8")
    signature = calculate_hmac_signature(raw_json)

    url = reverse("intelligent_tracker_api:video_gallery_register")
    response = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=signature,
    )

    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["status"] == "success"
    video_id = resp_data["video_id"]
    assert resp_data["stream_gateway_url"] == f"/api/v1/gallery/stream/{video_id}/"

    # Verify VideoItem created with zero copy
    video_item = VideoItem.objects.get(id=video_id)
    assert video_item.title == "Intrusion Sliced Clip - Cam North 01"
    assert video_item.source_type == VideoItem.SOURCE_MP4
    assert video_item.embed_url == "http://192.168.1.150:8000/clips/intrusion_101.mp4"
    assert not bool(video_item.video_file)  # Zero disk duplication!
    assert bool(video_item.thumbnail)  # Thumbnail was decoded and saved

    # Verify linkage to SecurityEvent
    event.refresh_from_db()
    assert event.video_evidence == video_item
    assert len(event.metadata["trajectory"]) == 3
    assert event.metadata["video_duration"] == 18.5
    assert event.metadata["video_registered"] is True

    # Verify audit log
    assert SecurityAuditLog.objects.filter(signature_valid=True, endpoint=url).exists()


def test_video_evidence_register_tampered_hmac(client, db):
    """
    Validates HMAC verification failure on tampered registration payload.
    """
    payload = {
        "title": "Unauthorized Registration",
        "source_url": "http://edge/clip.mp4",
    }
    url = reverse("intelligent_tracker_api:video_gallery_register")
    response = client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE="tampered_signature_hex_12345",
    )
    assert response.status_code == 401


def test_video_evidence_stream_gateway_remote_proxy(client, db):
    """
    Validates on-demand streaming reverse proxy with range forwarding.
    """
    gallery = VideoGallery.objects.create(name="Proxy Gallery", slug="proxy-gallery")
    item = VideoItem.objects.create(
        gallery=gallery,
        title="Remote Edge Clip",
        source_type=VideoItem.SOURCE_MP4,
        embed_url="http://192.168.1.50:8000/clips/event_99.mp4",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 206
    mock_resp.headers = {
        "Content-Type": "video/mp4",
        "Content-Range": "bytes 0-15/100",
        "Content-Length": "16",
        "Accept-Ranges": "bytes",
    }
    mock_resp.iter_content.return_value = [b"STREAMED_CHUNK_A", b"STREAMED_CHUNK_B"]

    with patch("intelligent_tracker_hub.api_views.requests.get", return_value=mock_resp) as mock_get:
        url = reverse("intelligent_tracker_api:video_gallery_stream", kwargs={"video_id": item.id})
        response = client.get(url, HTTP_RANGE="bytes=0-15")

        assert response.status_code == 206
        assert response["Content-Range"] == "bytes 0-15/100"
        assert response["Content-Length"] == "16"
        content = b"".join(response.streaming_content)
        assert content == b"STREAMED_CHUNK_ASTREAMED_CHUNK_B"
        mock_get.assert_called_once()


def test_video_evidence_stream_gateway_local_archived(client, db):
    """
    Validates streaming gateway on locally archived file with byte-range slicing.
    """
    gallery = VideoGallery.objects.create(name="Vault Gallery", slug="vault-gallery")
    video_content = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    item = VideoItem.objects.create(
        gallery=gallery,
        title="Archived Local Clip",
        source_type=VideoItem.SOURCE_MP4,
        video_file=ContentFile(video_content, name="sample_vault.mp4"),
    )

    url = reverse("intelligent_tracker_api:video_gallery_stream", kwargs={"video_id": item.id})

    # Full request
    resp_full = client.get(url)
    assert resp_full.status_code == 200
    assert b"".join(resp_full.streaming_content) == video_content

    # Range request (bytes 5-15)
    resp_range = client.get(url, HTTP_RANGE="bytes=5-15")
    assert resp_range.status_code == 206
    assert resp_range["Content-Range"] == f"bytes 5-15/{len(video_content)}"
    assert resp_range["Content-Length"] == "11"
    assert b"".join(resp_range.streaming_content) == b"56789ABCDEF"


def test_video_evidence_archive_action(client, db):
    """
    Validates on-demand dual-mode cloud archival pulling remote video into Hub storage.
    """
    gallery = VideoGallery.objects.create(name="Archival Gallery", slug="archival-gallery")
    item = VideoItem.objects.create(
        gallery=gallery,
        title="Edge Clip for Freezing",
        source_type=VideoItem.SOURCE_MP4,
        embed_url="http://192.168.1.50:8000/clips/freeze_me.mp4",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"FROZEN_MP4_EVIDENCE_BYTES_12345"

    with patch("intelligent_tracker_hub.api_views.requests.get", return_value=mock_resp):
        url = reverse("intelligent_tracker_api:video_gallery_archive", kwargs={"video_id": item.id})
        response = client.post(url)
        assert response.status_code == 200
        assert response.json()["status"] == "archived"

        item.refresh_from_db()
        assert bool(item.video_file) is True

        # Second call returns already_archived
        resp2 = client.post(url)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "already_archived"


def test_video_evidence_upload_multipart(client, auth_user, test_location):
    """
    Validates traditional multipart/form-data upload for isolated edge nodes.
    """
    client.force_login(auth_user)
    dummy_file = SimpleUploadedFile("direct_evidence.mp4", b"BINARY_MP4_DIRECT_BYTES", content_type="video/mp4")

    url = reverse("intelligent_tracker_api:video_gallery_upload")
    response = client.post(
        url,
        {
            "file": dummy_file,
            "title": "Direct Multipart Incident Clip",
            "site_code": test_location.code,
            "camera_id": "cam-direct-01",
        },
        format="multipart",
    )
    assert response.status_code == 201
    resp_data = response.json()
    assert resp_data["status"] == "success"
    video_id = resp_data["video_id"]

    item = VideoItem.objects.get(id=video_id)
    assert item.title == "Direct Multipart Incident Clip"
    assert bool(item.video_file) is True


def test_event_detail_view_renders_video_evidence(client, auth_user, test_location):
    """
    Validates that event detail view renders HTML5 video player and trajectory telemetry.
    """
    client.force_login(auth_user)
    gallery = VideoGallery.objects.create(name="Detail Gallery", slug="detail-gallery")
    item = VideoItem.objects.create(
        gallery=gallery,
        title="Intrusion Video Detail",
        source_type=VideoItem.SOURCE_MP4,
        embed_url="http://192.168.1.50:8000/clips/test_detail.mp4",
    )
    event = SecurityEvent.objects.create(
        event_id=uuid.uuid4(),
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-detail-01",
        severity=SecuritySeverity.CRITICAL,
        video_evidence=item,
        metadata={
            "trajectory": [{"x": 1, "y": 2}, {"x": 3, "y": 4}],
            "dwell_seconds": 10.0,
        },
    )

    url = reverse("intelligent_tracker_hub:event_detail", kwargs={"event_id": event.event_id})
    response = client.get(url)
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert "Video Evidence Stream" in html
    assert f"/api/v1/gallery/stream/{item.id}/" in html
    assert "Archive to Cloud Vault" in html
    assert "Ground-Plane Homography Trajectory" in html
    assert "2 Waypoints" in html

