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
    Camera,
    CameraStatus,
    VisitorAccessLog,
    AccessDirection,
    VerificationMethod,
)
from intelligent_tracker_hub.security import (
    calculate_hmac_signature,
    verify_hmac_signature,
    get_tracker_secret_key,
)
from intelligent_tracker_hub.notifications import send_visitor_arrival_notification
from intelligent_tracker_hub.plugin import IntelligentTrackerPlugin
from crm.models import (
    Contact,
    Company,
    SecurityClearance,
    PresenceStatus,
    InteractionLog,
    InteractionType,
)
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


def test_video_evidence_corruption_auto_fallback_to_reference(client, db):
    """
    Validates that if local video file on disk is deleted or 0 bytes,
    the streaming gateway and direct URL automatically recover by streaming from the source reference.
    """
    gallery = VideoGallery.objects.create(name="Resilience Gallery", slug="resilience-gallery")
    # Empty 0-byte file simulating a corrupted or truncated write
    empty_corrupted_file = ContentFile(b"", name="corrupted_0byte.mp4")
    item = VideoItem.objects.create(
        gallery=gallery,
        title="Corrupted Local Clip",
        source_type=VideoItem.SOURCE_MP4,
        embed_url="http://192.168.1.150:8000/clips/int_42.mp4",
        video_file=empty_corrupted_file,
    )

    # 1. VideoItem model health detection
    assert item.is_local_file_healthy is False
    # direct_media_url automatically falls back to source reference
    assert item.direct_media_url == "http://192.168.1.150:8000/clips/int_42.mp4"

    # 2. Gateway auto-fallback
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {
        "Content-Type": "video/mp4",
        "Content-Length": "28",
        "Accept-Ranges": "bytes",
    }
    mock_resp.iter_content.return_value = [b"REMOTE_FALLBACK_VIDEO_STREAM"]

    with patch("intelligent_tracker_hub.api_views.requests.get", return_value=mock_resp) as mock_get:
        url = reverse("intelligent_tracker_api:video_gallery_stream", kwargs={"video_id": item.id})
        response = client.get(url)

        assert response.status_code == 200
        assert response["X-Evidence-Source"] == "edge-fallback"
        content = b"".join(response.streaming_content)
        assert content == b"REMOTE_FALLBACK_VIDEO_STREAM"
        mock_get.assert_called_once()


def test_video_evidence_forced_repair_from_reference(client, db):
    """
    Validates that an operator or automated monitor can force repair
    a local archive from the remote reference URL via ?force=true.
    """
    gallery = VideoGallery.objects.create(name="Repair Gallery", slug="repair-gallery")
    item = VideoItem.objects.create(
        gallery=gallery,
        title="Corrupted File to Repair",
        source_type=VideoItem.SOURCE_MP4,
        embed_url="http://192.168.1.150:8000/clips/int_99.mp4",
        video_file=ContentFile(b"OLD_DAMAGED_DATA", name="broken.mp4"),
    )

    # Calling without force when file exists returns already_archived
    url = reverse("intelligent_tracker_api:video_gallery_archive", kwargs={"video_id": item.id})
    resp_unforced = client.post(url)
    assert resp_unforced.status_code == 200
    assert resp_unforced.json()["status"] == "already_archived"

    # Calling with ?force=true downloads fresh copy from source reference and verifies SHA-256
    repaired_bytes = b"FRESH_VERIFIED_MP4_STREAM_CONTENT_9999"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = repaired_bytes

    with patch("intelligent_tracker_hub.api_views.requests.get", return_value=mock_resp):
        resp_forced = client.post(f"{url}?force=true")
        assert resp_forced.status_code == 200
        data = resp_forced.json()
        assert data["status"] == "archived"
        assert data["repaired"] is True
        assert data["size_bytes"] == len(repaired_bytes)
        assert "sha256" in data

        item.refresh_from_db()
        assert item.video_file.read() == repaired_bytes


# ==============================================================================
# 8. Milestone 16c (Phase E3) Camera Registry, Live Stream Gateway & Telemetry Tests
# ==============================================================================


def test_camera_model_creation_and_properties(db, test_location):
    """
    Validates Camera model creation, status badges, liveness detection, and URLs.
    """
    camera = Camera.objects.create(
        camera_id="cam-north-01",
        name="North Perimeter Camera",
        site=test_location,
        stream_url="http://192.168.1.100:8000/stream/cam1/",
        status=CameraStatus.ONLINE,
        fps=30,
        resolution="1920x1080",
        last_heartbeat=timezone.now(),
    )

    assert str(camera) == "North Perimeter Camera (cam-north-01)"
    assert camera.is_alive is True
    assert camera.status_badge_class == "success"
    assert camera.get_stream_proxy_url() == "/api/v1/security/stream/live/cam-north-01/"
    assert camera.get_telemetry_url() == "/api/v1/security/stream/telemetry/cam-north-01/"

    # Test SecurityEvent.camera_obj property resolution
    event = SecurityEvent.objects.create(
        event_id=uuid.uuid4(),
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-north-01",
    )
    assert event.camera_obj == camera


def test_camera_heartbeat_api_unauthorized(client, db):
    """
    Validates that camera heartbeat endpoint rejects requests without signature or user auth.
    """
    url = reverse("intelligent_tracker_api:camera_heartbeat")
    response = client.post(
        url,
        {"camera_id": "cam-test-01", "status": "ONLINE"},
        content_type="application/json",
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_camera_heartbeat_api_hmac_success(client, db, test_location):
    """
    Validates successful camera heartbeat registration and update via HMAC signature.
    """
    payload = {
        "camera_id": "cam-gate-02",
        "name": "Gate 02 Primary Ingress",
        "status": "ONLINE",
        "fps": 25,
        "resolution": "1920x1080",
        "stream_url": "http://192.168.1.102:8000/live/",
        "site_code": test_location.code,
        "metadata": {"gpu_temp": 52.4, "dropped_frames": 0},
    }
    raw_json = json.dumps(payload).encode("utf-8")
    signature = calculate_hmac_signature(raw_json)

    url = reverse("intelligent_tracker_api:camera_heartbeat")
    response = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=f"sha256={signature}",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["camera_id"] == "cam-gate-02"
    assert data["is_alive"] is True

    # Check database persistence
    camera = Camera.objects.get(camera_id="cam-gate-02")
    assert camera.name == "Gate 02 Primary Ingress"
    assert camera.site == test_location
    assert camera.fps == 25
    assert camera.metadata["gpu_temp"] == 52.4

    # Verify audit log recorded
    audit = SecurityAuditLog.objects.filter(event_id="heartbeat_cam-gate-02").first()
    assert audit is not None
    assert audit.signature_valid is True
    assert audit.status_code == 200


def test_camera_viewset_list_and_filter(client, auth_user, test_location):
    """
    Validates CameraViewSet REST endpoint for listing and filtering cameras.
    """
    client.force_login(auth_user)
    Camera.objects.create(
        camera_id="cam-list-01",
        name="Lobby Camera",
        site=test_location,
        status=CameraStatus.ONLINE,
    )
    Camera.objects.create(
        camera_id="cam-list-02",
        name="Parking Camera",
        status=CameraStatus.OFFLINE,
    )

    url = "/api/v1/security/cameras/"
    resp = client.get(url)
    assert resp.status_code == 200
    results = resp.json()["results"] if "results" in resp.json() else resp.json()
    assert len(results) >= 2

    # Filter by status
    resp_offline = client.get(f"{url}?status=OFFLINE")
    assert resp_offline.status_code == 200
    offline_results = resp_offline.json()["results"] if "results" in resp_offline.json() else resp_offline.json()
    assert any(c["camera_id"] == "cam-list-02" for c in offline_results)


def test_live_stream_proxy_synthetic_stream(client, db):
    """
    Validates that LiveStreamProxyApiView returns multipart MJPEG stream with valid JPEG frames.
    """
    Camera.objects.create(
        camera_id="cam-synth-01",
        name="Synthetic Feed",
        stream_url="mock://",
        status=CameraStatus.ONLINE,
    )

    url = reverse("intelligent_tracker_api:camera_stream_live", kwargs={"camera_id": "cam-synth-01"})
    response = client.get(f"{url}?single_frame=1")

    assert response.status_code == 200
    assert response["Content-Type"] == "multipart/x-mixed-replace; boundary=frame"
    assert response["X-Camera-ID"] == "cam-synth-01"
    assert response["X-Stream-Source"] == "synthetic-mock"

    # Verify frame content contains JPEG markers
    content = b"".join(response.streaming_content)
    assert b"--frame\r\n" in content
    assert b"Content-Type: image/jpeg\r\n" in content
    assert b"\xff\xd8" in content  # Standard JPEG Start of Image (SOI) marker


def test_live_stream_proxy_fallback_on_unreachable_edge(client, db):
    """
    Validates that if edge stream URL fails to connect, gateway gracefully falls back to synthetic stream.
    """
    Camera.objects.create(
        camera_id="cam-failing-01",
        name="Failing Edge Cam",
        stream_url="http://10.254.254.254:9999/broken/stream.mjpeg",
        status=CameraStatus.ONLINE,
    )

    url = reverse("intelligent_tracker_api:camera_stream_live", kwargs={"camera_id": "cam-failing-01"})
    # Mock requests.get raising connection error
    with patch("intelligent_tracker_hub.api_views.requests.get", side_effect=Exception("Connection timed out")):
        response = client.get(f"{url}?single_frame=1")
        assert response.status_code == 200
        content = b"".join(response.streaming_content)
        assert b"--frame\r\n" in content
        assert b"\xff\xd8" in content


def test_live_telemetry_stream_api(client, db, test_location):
    """
    Validates real-time telemetry API delivering bounding boxes, track labels, and active alert overlays.
    """
    camera = Camera.objects.create(
        camera_id="cam-telem-01",
        name="Telemetry Gate Cam",
        site=test_location,
        status=CameraStatus.ONLINE,
        fps=30,
        resolution="1920x1080",
    )
    # Create an active intrusion event
    SecurityEvent.objects.create(
        event_id=uuid.uuid4(),
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-telem-01",
        severity=SecuritySeverity.CRITICAL,
        metadata={"zone_name": "Vault Perimeter", "dwell_seconds": 15.2, "confidence": 0.98},
        is_resolved=False,
    )

    url = reverse("intelligent_tracker_api:camera_telemetry_live", kwargs={"camera_id": "cam-telem-01"})
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["camera_id"] == "cam-telem-01"
    assert data["fps"] == 30
    assert data["resolution"] == "1920x1080"
    assert len(data["active_tracks"]) >= 2  # Staff track + Intrusion track

    intrusion_track = next(t for t in data["active_tracks"] if t["status"] == "intrusion")
    assert intrusion_track["color"] == "#ef4444"
    assert "Intrusion Alert" in intrusion_track["label"]
    assert data["zones"][0]["status"] == "ALARM"
    assert data["zones"][0]["name"] == "Vault Perimeter"


def test_soc_dashboard_view_camera_grid(client, auth_user, test_location):
    """
    Validates SOC Dashboard rendering multi-camera video matrix, site selectors, and layout modes.
    """
    client.force_login(auth_user)
    Camera.objects.create(
        camera_id="cam-soc-01",
        name="Main Lobby",
        site=test_location,
        status=CameraStatus.ONLINE,
        fps=30,
    )

    url = reverse("intelligent_tracker_hub:dashboard")

    # 1. Default grid view
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "Multi-Camera Surveillance Matrix" in html
    assert "Main Lobby" in html
    assert "cam-soc-01" in html
    assert "canvas-overlay-cam-soc-01" in html

    # 2. Filter by site
    resp_site = client.get(f"{url}?site_id={test_location.id}")
    assert resp_site.status_code == 200
    assert "Main Lobby" in resp_site.content.decode("utf-8")

    # 3. Solo layout mode
    resp_solo = client.get(f"{url}?layout=solo")
    assert resp_solo.status_code == 200
    assert "col-12" in resp_solo.content.decode("utf-8")


# ==============================================================================
# 5. Milestone 16d (Phase E4) CRM Visitor Passes & Whitelist Delta-Sync Tests
# ==============================================================================

@pytest.fixture
def test_company(db):
    return Company.objects.create(
        name="Cyberdyne Systems",
        industry="Autonomous Defense",
        city="Austin",
        country="United States",
    )


@pytest.fixture
def test_contacts(db, test_company, test_location):
    c1 = Contact.objects.create(
        first_name="Sarah",
        last_name="Connor",
        email="sconnor@example.com",
        company=test_company,
        security_clearance=SecurityClearance.VIP,
        license_plate="TX-999-VIP",
        security_tag="exec-zone",
        face_embedding_vector=[0.05] * 512,
    )
    c2 = Contact.objects.create(
        first_name="Kyle",
        last_name="Reese",
        email="kreese@example.com",
        company=test_company,
        security_clearance=SecurityClearance.CONTRACTOR,
        license_plate="CA-123-KLR",
        security_tag="contractor-gate",
        valid_from=timezone.now() - timezone.timedelta(days=2),
        valid_until=timezone.now() + timezone.timedelta(days=5),
    )
    c3 = Contact.objects.create(
        first_name="Expired",
        last_name="Visitor",
        email="expired@example.com",
        company=test_company,
        security_clearance=SecurityClearance.VISITOR,
        valid_from=timezone.now() - timezone.timedelta(days=10),
        valid_until=timezone.now() - timezone.timedelta(days=1),
    )
    c4 = Contact.objects.create(
        first_name="Miles",
        last_name="Dyson",
        email="mdyson@example.com",
        company=test_company,
        security_clearance=SecurityClearance.BANNED,
        license_plate="BANNED-01",
    )
    return [c1, c2, c3, c4]


def test_crm_contact_physical_security_credentials_and_methods(db, test_location):
    contact = Contact.objects.create(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        security_clearance=SecurityClearance.VIP,
        license_plate="abc-1234",
        security_tag="secure-zone-a",
        valid_from=timezone.now() - timezone.timedelta(hours=1),
        valid_until=timezone.now() + timezone.timedelta(days=1),
    )

    assert contact.normalized_license_plate == "ABC1234"
    assert contact.is_pass_valid is True
    assert contact.presence_status == PresenceStatus.OFF_PREMISES
    assert contact.presence_badge_class == "secondary"
    assert "warning" in contact.clearance_badge_class

    # Test check_in
    contact.check_in(location=test_location, verification_method="face", gate_camera_id="cam-gate-01")
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.ON_PREMISES
    assert contact.presence_badge_class == "success"
    assert contact.last_seen_location == test_location
    assert contact.last_seen_at is not None

    # Verify InteractionLog
    interaction = InteractionLog.objects.filter(contact=contact, interaction_type=InteractionType.SECURITY_ACCESS).first()
    assert interaction is not None
    assert "Entry" in interaction.summary
    assert "Face" in interaction.summary

    # Test check_out
    contact.check_out(location=test_location, verification_method="plate", gate_camera_id="cam-gate-01")
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.OFF_PREMISES

    # Test pass validity window
    contact.valid_until = timezone.now() - timezone.timedelta(minutes=5)
    contact.save()
    assert contact.is_pass_valid is False

    # Banned contact is always invalid
    contact.valid_until = timezone.now() + timezone.timedelta(days=10)
    contact.security_clearance = SecurityClearance.BANNED
    contact.save()
    assert contact.is_pass_valid is False


def test_visitor_access_log_model(db, test_location):
    contact = Contact.objects.create(
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        security_clearance=SecurityClearance.STAFF,
    )
    log = VisitorAccessLog.objects.create(
        contact=contact,
        site=test_location,
        camera_id="cam-north-01",
        direction=AccessDirection.ENTRY,
        verification_method=VerificationMethod.FACE,
        recognized_identifier=contact.full_name,
        confidence=0.98,
        access_granted=True,
    )

    assert str(log.access_id) in str(log) or "Alice Smith" in str(log)
    assert log.status_badge_class == "success"
    assert log.access_granted is True


def test_whitelist_delta_sync_api_unauthorized(client):
    url = reverse("intelligent_tracker_api:security_whitelist")
    resp = client.get(url)
    assert resp.status_code == 401


def test_whitelist_delta_sync_api_success_and_etag(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_whitelist")
    secret = get_tracker_secret_key()
    sig = calculate_hmac_signature(b"", secret=secret)

    # 1. Initial full fetch
    resp = client.get(
        f"{url}?site_id={test_location.id}",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "whitelist" in data
    assert "version_hash" in data
    assert "revoked_ids" in data
    assert "ETag" in resp.headers

    etag = resp.headers["ETag"]
    assert len(etag) > 10

    # 2. Re-request with matching If-None-Match header -> 304 Not Modified
    resp_304 = client.get(
        f"{url}?site_id={test_location.id}",
        HTTP_X_TRACKER_SIGNATURE=sig,
        HTTP_IF_NONE_MATCH=etag,
    )
    assert resp_304.status_code == 304
    assert resp_304.content == b""


def test_whitelist_delta_sync_api_filters_expired_passes_and_marks_banned(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_whitelist")
    secret = get_tracker_secret_key()
    sig = calculate_hmac_signature(b"", secret=secret)

    resp = client.get(
        f"{url}?site_id={test_location.id}",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 200
    data = resp.json()

    whitelist = data["whitelist"]
    contact_emails = [c["email"] for c in whitelist]

    # Active VIP and Contractor are in whitelist
    assert "sconnor@example.com" in contact_emails
    assert "kreese@example.com" in contact_emails

    # Expired Visitor pass is EXCLUDED from active whitelist
    assert "expired@example.com" not in contact_emails

    # Banned contact is included with is_banned: true so edge immediately denies
    banned_item = next((c for c in whitelist if c["email"] == "mdyson@example.com"), None)
    assert banned_item is not None
    assert banned_item["is_banned"] is True
    assert banned_item["security_clearance"] == "BANNED"

    # Expired contact ID must be in revoked_ids
    expired_contact = next(c for c in test_contacts if c.email == "expired@example.com")
    assert expired_contact.id in data["revoked_ids"]


def test_whitelist_delta_sync_api_since_parameter(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_whitelist")
    secret = get_tracker_secret_key()
    sig = calculate_hmac_signature(b"", secret=secret)

    import time
    import urllib.parse
    time.sleep(0.02)
    cutoff = timezone.now()
    time.sleep(0.02)

    # Update only one contact
    c1 = test_contacts[0]
    c1.security_tag = "new-updated-tag"
    c1.save()

    encoded_since = urllib.parse.quote(cutoff.isoformat())
    resp = client.get(
        f"{url}?since={encoded_since}",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["whitelist"]) == 1
    assert data["whitelist"][0]["contact_id"] == c1.id
    assert data["whitelist"][0]["security_tag"] == "new-updated-tag"


def test_security_access_ingest_api_unauthorized(client):
    url = reverse("intelligent_tracker_api:security_access")
    resp = client.post(
        url,
        data={"camera_id": "cam-gate-01"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_security_access_ingest_entry_granted_and_presence_update(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    contact = test_contacts[0]  # Sarah Connor (VIP)

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-gate-entry-01",
        "contact_id": contact.id,
        "direction": "ENTRY",
        "verification_method": "face",
        "confidence": 0.99,
        "access_granted": True,
        "metadata": {"turnstile": 2},
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_granted"] is True
    assert data["direction"] == "ENTRY"
    assert data["contact"] == contact.id

    # Verify contact presence in DB
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.ON_PREMISES
    assert contact.last_seen_location == test_location

    # Verify InteractionLog
    interaction = InteractionLog.objects.filter(contact=contact, interaction_type=InteractionType.SECURITY_ACCESS).first()
    assert interaction is not None
    assert "cam-gate-entry-01" in interaction.details


def test_security_access_ingest_exit_and_presence_update(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    contact = test_contacts[0]
    contact.presence_status = PresenceStatus.ON_PREMISES
    contact.save()

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-gate-exit-01",
        "contact_id": contact.id,
        "direction": "EXIT",
        "verification_method": "face",
        "confidence": 0.97,
        "access_granted": True,
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.OFF_PREMISES


def test_security_access_ingest_by_license_plate_anpr(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    contact = test_contacts[1]  # Kyle Reese (CA-123-KLR)

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-anpr-gate",
        "license_plate": "CA 123 KLR",  # Spaced format
        "direction": "ENTRY",
        "verification_method": "plate",
        "confidence": 0.94,
        "access_granted": True,
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["contact"] == contact.id
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.ON_PREMISES


def test_security_access_ingest_banned_contact_escalates_to_security_event(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    banned_contact = test_contacts[3]  # Miles Dyson (BANNED)

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-gate-01",
        "contact_id": banned_contact.id,
        "direction": "ENTRY",
        "verification_method": "face",
        "confidence": 0.96,
        "access_granted": True,  # Edge might optimistically request, hub must deny!
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_granted"] is False
    assert "Banned" in data["denial_reason"]

    # Contact must remain OFF_PREMISES
    banned_contact.refresh_from_db()
    assert banned_contact.presence_status == PresenceStatus.OFF_PREMISES

    # Verify a CRITICAL SecurityEvent was automatically created!
    sec_event = SecurityEvent.objects.filter(
        event_type=SecurityEventType.RESTRICTED_ENTITY,
        severity=SecuritySeverity.CRITICAL,
    ).first()
    assert sec_event is not None
    assert sec_event.metadata.get("contact_id") == banned_contact.id


def test_visitor_arrival_notification_service(db, test_contacts, test_location, mailoutbox):
    contact = test_contacts[0]
    log = VisitorAccessLog.objects.create(
        contact=contact,
        site=test_location,
        camera_id="cam-gate-01",
        direction=AccessDirection.ENTRY,
        verification_method=VerificationMethod.FACE,
        access_granted=True,
    )

    sent = send_visitor_arrival_notification(contact, log)
    assert sent is True
    assert len(mailoutbox) == 1
    email = mailoutbox[0]
    assert "Sarah Connor" in email.subject
    assert "[ENGLISH]" in email.body
    assert "[ESPAÑOL]" in email.body
    assert "NOTIFICACIÓN DE ACCESO" in email.body.upper()


def test_visitor_access_catalog_viewset(client, auth_user, test_contacts, test_location):
    client.force_login(auth_user)
    VisitorAccessLog.objects.create(
        contact=test_contacts[0],
        site=test_location,
        camera_id="cam-catalog-01",
        direction=AccessDirection.ENTRY,
        verification_method=VerificationMethod.FACE,
        access_granted=True,
    )

    url = "/api/v1/security/access/catalog/"
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1



