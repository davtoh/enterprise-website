import json
import uuid
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone

from intelligent_tracker_hub.models import (
    Camera,
    CameraStatus,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityAuditLog,
)
from intelligent_tracker_hub.security import calculate_hmac_signature


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

