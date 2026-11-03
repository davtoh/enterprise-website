import json
import uuid
from unittest.mock import patch, MagicMock
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from intelligent_tracker_hub.models import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityAuditLog,
)
from intelligent_tracker_hub.security import calculate_hmac_signature
from video_gallery.models import VideoGallery, VideoItem
from .conftest import SAMPLE_PNG_BASE64


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

