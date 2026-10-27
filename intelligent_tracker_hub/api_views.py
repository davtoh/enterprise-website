import base64
import hmac
import json
import os
import re
import uuid
import requests
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import SecurityEvent, SecurityEventType, SecuritySeverity, SecurityAuditLog
from .serializers import (
    SecurityEventWebhookSerializer,
    SecurityEventSerializer,
    SecurityAuditLogSerializer,
    VideoEvidenceRegisterSerializer,
    VideoEvidenceUploadSerializer,
)
from .security import verify_hmac_signature, get_client_ip, calculate_hmac_signature, get_tracker_secret_key
from location_management.models import Location
from video_gallery.models import VideoGallery, VideoItem


class SecurityEventWebhookApiView(APIView):
    """
    Webhook receiver endpoint for edge AI vision nodes (intelligent-tracker).
    Requires a valid HMAC-SHA256 signature in the X-Tracker-Signature HTTP header.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        raw_body = request.body
        signature_header = (
            request.headers.get("X-Tracker-Signature")
            or request.META.get("HTTP_X_TRACKER_SIGNATURE", "")
        )

        # 1. HMAC Signature Verification
        is_signature_valid = verify_hmac_signature(raw_body, signature_header)
        if not is_signature_valid:
            SecurityAuditLog.objects.create(
                ip_address=client_ip,
                endpoint=request.path,
                http_method=request.method,
                signature_header=signature_header,
                signature_valid=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_message="Missing or invalid X-Tracker-Signature HMAC signature.",
                raw_payload=raw_body.decode("utf-8", errors="replace")[:5000],
                processed_successfully=False,
            )
            return Response(
                {
                    "error": "Unauthorized",
                    "detail": "Missing or invalid X-Tracker-Signature HMAC-SHA256 signature.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 2. Schema Validation
        serializer = SecurityEventWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            SecurityAuditLog.objects.create(
                ip_address=client_ip,
                endpoint=request.path,
                http_method=request.method,
                signature_header=signature_header,
                signature_valid=True,
                status_code=status.HTTP_400_BAD_REQUEST,
                error_message=json.dumps(serializer.errors),
                raw_payload=raw_body.decode("utf-8", errors="replace")[:5000],
                processed_successfully=False,
            )
            return Response(
                {"error": "Bad Request", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        event_id = data.get("event_id") or uuid.uuid4()
        event_type = data["event_type"]
        camera_id = data["camera_id"]
        event_timestamp = data.get("timestamp") or timezone.now()
        metadata = data.get("metadata") or {}

        # 3. Derive Severity if not explicitly specified
        severity = data.get("severity")
        if not severity:
            if metadata.get("severity") in SecuritySeverity.values:
                severity = metadata["severity"]
            elif event_type == SecurityEventType.FALL_DETECTED:
                severity = SecuritySeverity.CRITICAL
            elif event_type in (SecurityEventType.INTRUSION, SecurityEventType.RESTRICTED_ENTITY):
                severity = SecuritySeverity.HIGH
            elif event_type in (SecurityEventType.OCCUPANCY_THRESHOLD, SecurityEventType.LOITERING):
                severity = SecuritySeverity.MEDIUM
            else:
                severity = SecuritySeverity.LOW

        # 4. Resolve Location Site
        site_obj = None
        site_id = data.get("site_id")
        site_code = data.get("site_code")
        if site_id:
            site_obj = Location.objects.filter(id=site_id).first()
        if not site_obj and site_code:
            site_obj = Location.objects.filter(code=site_code).first()

        # 5. Build and Save SecurityEvent
        security_event = SecurityEvent(
            event_id=event_id,
            event_type=event_type,
            site=site_obj,
            camera_id=camera_id,
            timestamp=event_timestamp,
            metadata=metadata,
            severity=severity,
        )

        # 6. Process Evidence Snapshot (Base64 JPEG/PNG)
        snapshot_base64 = data.get("snapshot_base64")
        if snapshot_base64:
            try:
                if ";base64," in snapshot_base64:
                    _, b64data = snapshot_base64.split(";base64,", 1)
                else:
                    b64data = snapshot_base64
                decoded_img = base64.b64decode(b64data)
                filename = f"{event_id}.jpg"
                security_event.snapshot.save(filename, ContentFile(decoded_img), save=False)
            except Exception as e:
                metadata["snapshot_decode_error"] = str(e)

        security_event.save()

        # 7. Record Audit Trail
        SecurityAuditLog.objects.create(
            ip_address=client_ip,
            endpoint=request.path,
            http_method=request.method,
            signature_header=signature_header,
            signature_valid=True,
            event_id=str(security_event.event_id),
            status_code=status.HTTP_201_CREATED,
            raw_payload=raw_body.decode("utf-8", errors="replace")[:5000],
            processed_successfully=True,
        )

        return Response(
            {
                "status": "success",
                "event_id": str(security_event.event_id),
                "event_type": security_event.event_type,
                "severity": security_event.severity,
                "camera_id": security_event.camera_id,
                "timestamp": security_event.timestamp.isoformat(),
                "message": "Security event ingested successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only REST endpoint to list and retrieve SecurityEvent records.
    Supports filtering by event_type, severity, is_resolved, camera_id, and site_id.
    """

    queryset = SecurityEvent.objects.select_related("site", "resolved_by").all()
    serializer_class = SecurityEventSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        event_type = self.request.query_params.get("event_type")
        severity = self.request.query_params.get("severity")
        is_resolved = self.request.query_params.get("is_resolved")
        camera_id = self.request.query_params.get("camera_id")
        site_id = self.request.query_params.get("site_id")

        if event_type:
            qs = qs.filter(event_type=event_type)
        if severity:
            qs = qs.filter(severity=severity)
        if is_resolved is not None:
            if is_resolved.lower() in ("true", "1", "yes"):
                qs = qs.filter(is_resolved=True)
            elif is_resolved.lower() in ("false", "0", "no"):
                qs = qs.filter(is_resolved=False)
        if camera_id:
            qs = qs.filter(camera_id=camera_id)
        if site_id:
            qs = qs.filter(site_id=site_id)

        return qs


class SecurityAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only REST endpoint to inspect edge webhook audit logs.
    """

    queryset = SecurityAuditLog.objects.all()
    serializer_class = SecurityAuditLogSerializer


class SecurityStatsApiView(APIView):
    """
    Aggregated KPIs and event metrics for security operations center dashboards.
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        total_events = SecurityEvent.objects.count()
        unresolved_events = SecurityEvent.objects.filter(is_resolved=False).count()
        critical_events = SecurityEvent.objects.filter(severity=SecuritySeverity.CRITICAL, is_resolved=False).count()
        high_events = SecurityEvent.objects.filter(severity=SecuritySeverity.HIGH, is_resolved=False).count()

        by_type = dict(
            SecurityEvent.objects.values("event_type")
            .annotate(count=Count("id"))
            .values_list("event_type", "count")
        )

        recent_events = (
            SecurityEvent.objects.select_related("site")
            .order_by("-timestamp")[:5]
            .values("event_id", "event_type", "severity", "camera_id", "timestamp", "is_resolved")
        )

        return Response(
            {
                "total_events": total_events,
                "unresolved_events": unresolved_events,
                "critical_events": critical_events,
                "high_events": high_events,
                "events_by_type": by_type,
                "recent_alerts": list(recent_events),
            }
        )


class VideoEvidenceRegisterApiView(APIView):
    """
    Zero-Copy Video Evidence Registration API.
    Edge AI vision nodes register clip URLs directly without transferring heavy MP4 files to the Hub.
    Requires HMAC-SHA256 signature (X-Tracker-Signature).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        raw_body = request.body
        signature_header = (
            request.headers.get("X-Tracker-Signature")
            or request.META.get("HTTP_X_TRACKER_SIGNATURE", "")
        )

        # 1. HMAC Signature Verification
        if not verify_hmac_signature(raw_body, signature_header):
            SecurityAuditLog.objects.create(
                ip_address=client_ip,
                endpoint=request.path,
                http_method=request.method,
                signature_header=signature_header,
                signature_valid=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_message="Missing or invalid X-Tracker-Signature for video registration.",
                raw_payload=raw_body.decode("utf-8", errors="replace")[:5000],
                processed_successfully=False,
            )
            return Response(
                {
                    "error": "Unauthorized",
                    "detail": "Missing or invalid X-Tracker-Signature HMAC-SHA256 signature.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 2. Schema Validation
        serializer = VideoEvidenceRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            SecurityAuditLog.objects.create(
                ip_address=client_ip,
                endpoint=request.path,
                http_method=request.method,
                signature_header=signature_header,
                signature_valid=True,
                status_code=status.HTTP_400_BAD_REQUEST,
                error_message=json.dumps(serializer.errors),
                raw_payload=raw_body.decode("utf-8", errors="replace")[:5000],
                processed_successfully=False,
            )
            return Response(
                {"error": "Bad Request", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        event_id = data.get("event_id")
        title = data["title"]
        source_url = data["source_url"]
        site_id = data.get("site_id")
        site_code = data.get("site_code")
        site_name = data.get("site_name")
        camera_id = data.get("camera_id", "")
        duration_seconds = data.get("duration_seconds")
        thumbnail_base64 = data.get("thumbnail_base64")
        trajectory = data.get("trajectory", [])
        metadata = data.get("metadata", {})

        # 3. Resolve Site Location
        site_obj = None
        if site_id:
            site_obj = Location.objects.filter(id=site_id).first()
        if not site_obj and site_code:
            site_obj = Location.objects.filter(code=site_code).first()
        if not site_obj and site_name:
            site_obj = Location.objects.filter(name__iexact=site_name).first()

        site_label = site_obj.name if site_obj else (site_name or site_code or "Default Site")
        site_slug_part = site_obj.code if site_obj and site_obj.code else (site_code or site_name or "default")
        gallery_slug = slugify(f"security-audit-{site_slug_part}") or "security-audit-default"

        # 4. Resolve or Create VideoGallery
        gallery, _ = VideoGallery.objects.get_or_create(
            slug=gallery_slug,
            defaults={
                "name": f"Security Audit - {site_label}",
                "description": f"Surveillance video evidence and journey clips for {site_label}.",
            },
        )

        # 5. Build Description with camera, duration, and homography telemetry
        desc_parts = [f"Edge Video Evidence | Camera: {camera_id or 'Unknown'}"]
        if duration_seconds:
            desc_parts.append(f"Duration: {duration_seconds:.1f}s")
        if trajectory:
            desc_parts.append(f"Ground-Plane Homography Points: {len(trajectory)}")
        description = " | ".join(desc_parts)

        # 6. Create VideoItem (source_type=mp4, embed_url=source_url, zero disk copy)
        video_item = VideoItem(
            gallery=gallery,
            title=title,
            description=description,
            source_type=VideoItem.SOURCE_MP4,
            embed_url=source_url,
        )

        if thumbnail_base64:
            try:
                if ";base64," in thumbnail_base64:
                    _, b64data = thumbnail_base64.split(";base64,", 1)
                else:
                    b64data = thumbnail_base64
                decoded_thumb = base64.b64decode(b64data)
                thumb_name = f"thumb_ev_{uuid.uuid4().hex[:8]}.jpg"
                video_item.thumbnail.save(thumb_name, ContentFile(decoded_thumb), save=False)
            except Exception as e:
                metadata["thumbnail_decode_error"] = str(e)

        video_item.save()

        # 7. Associate with SecurityEvent if event_id provided
        if event_id:
            security_event = SecurityEvent.objects.filter(event_id=event_id).first()
            if security_event:
                security_event.video_evidence = video_item
                if trajectory:
                    security_event.metadata["trajectory"] = trajectory
                if duration_seconds:
                    security_event.metadata["video_duration"] = duration_seconds
                security_event.metadata["video_registered"] = True
                security_event.save(update_fields=["video_evidence", "metadata", "updated_at"])

        # 8. Record Audit Log
        SecurityAuditLog.objects.create(
            ip_address=client_ip,
            endpoint=request.path,
            http_method=request.method,
            signature_header=signature_header,
            signature_valid=True,
            event_id=str(event_id) if event_id else f"video_{video_item.id}",
            status_code=status.HTTP_201_CREATED,
            raw_payload=raw_body.decode("utf-8", errors="replace")[:5000],
            processed_successfully=True,
        )

        stream_url = f"/api/v1/gallery/stream/{video_item.id}/"
        return Response(
            {
                "status": "success",
                "video_id": video_item.id,
                "gallery_slug": gallery.slug,
                "gallery_name": gallery.name,
                "stream_gateway_url": stream_url,
                "source_url": video_item.embed_url,
                "event_id": str(event_id) if event_id else None,
                "message": "Video evidence registered successfully via zero-copy stream reference.",
            },
            status=status.HTTP_201_CREATED,
        )


class VideoEvidenceStreamGatewayApiView(APIView):
    """
    On-Demand Streaming Reverse Proxy Gateway.
    Proxies video from edge camera node or local media vault to client browser.
    Seamlessly forwards HTTP 206 Partial Content / Range requests for smooth scrubbing.
    """

    permission_classes = [AllowAny]

    def get(self, request, video_id, *args, **kwargs):
        video_item = get_object_or_404(VideoItem, pk=video_id)

        # Mode A: Locally archived file in media vault
        if video_item.video_file:
            try:
                file_path = video_item.video_file.path
                file_size = os.path.getsize(file_path)
            except Exception:
                file_size = None

            range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE", "")
            if range_header and file_size:
                match = re.match(r"bytes=(\d+)-(\d*)", range_header)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else file_size - 1
                    end = min(end, file_size - 1)
                    content_length = (end - start) + 1

                    def file_range_iterator(path, offset, length, chunk_size=65536):
                        with open(path, "rb") as f:
                            f.seek(offset)
                            remaining = length
                            while remaining > 0:
                                read_bytes = min(remaining, chunk_size)
                                data = f.read(read_bytes)
                                if not data:
                                    break
                                remaining -= len(data)
                                yield data

                    response = StreamingHttpResponse(
                        file_range_iterator(file_path, start, content_length),
                        status=status.HTTP_206_PARTIAL_CONTENT,
                        content_type="video/mp4",
                    )
                    response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
                    response["Content-Length"] = str(content_length)
                    response["Accept-Ranges"] = "bytes"
                    return response

            def full_file_iterator(path, chunk_size=65536):
                with open(path, "rb") as f:
                    while True:
                        data = f.read(chunk_size)
                        if not data:
                            break
                        yield data

            response = StreamingHttpResponse(
                full_file_iterator(video_item.video_file.path),
                status=status.HTTP_200_OK,
                content_type="video/mp4",
            )
            if file_size:
                response["Content-Length"] = str(file_size)
            response["Accept-Ranges"] = "bytes"
            return response

        # Mode B: Remote edge video stream (Zero-Copy Proxy)
        remote_url = video_item.embed_url
        if not remote_url or not (remote_url.startswith("http://") or remote_url.startswith("https://")):
            return Response(
                {"error": "Video has no accessible remote stream URL or local archive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        headers = {}
        range_header = request.headers.get("Range") or request.META.get("HTTP_RANGE", "")
        if range_header:
            headers["Range"] = range_header

        try:
            edge_resp = requests.get(remote_url, headers=headers, stream=True, timeout=(5, 30))
        except (requests.ConnectionError, requests.Timeout, requests.RequestException) as err:
            return Response(
                {
                    "error": "Edge video stream unreachable",
                    "detail": str(err),
                    "source_url": remote_url,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        def edge_stream_generator():
            try:
                for chunk in edge_resp.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk
            finally:
                edge_resp.close()

        status_code = (
            status.HTTP_206_PARTIAL_CONTENT
            if edge_resp.status_code == 206
            else status.HTTP_200_OK
        )
        response = StreamingHttpResponse(
            edge_stream_generator(),
            status=status_code,
            content_type=edge_resp.headers.get("Content-Type", "video/mp4"),
        )
        for h in ("Content-Range", "Content-Length", "Accept-Ranges"):
            if h in edge_resp.headers:
                response[h] = edge_resp.headers[h]
        if "Accept-Ranges" not in response:
            response["Accept-Ranges"] = "bytes"

        return response


class VideoEvidenceArchiveApiView(APIView):
    """
    Dual-Mode Cloud Archival API.
    Permanently pulls a remote edge video into central Hub storage for compliance/legal freezing.
    """

    permission_classes = [AllowAny]

    def post(self, request, video_id, *args, **kwargs):
        video_item = get_object_or_404(VideoItem, pk=video_id)

        # Check if already archived locally
        if video_item.video_file:
            return Response(
                {
                    "status": "already_archived",
                    "video_id": video_item.id,
                    "file_url": video_item.video_file.url,
                    "message": "Video is already archived in local storage.",
                },
                status=status.HTTP_200_OK,
            )

        remote_url = video_item.embed_url
        if not remote_url or not (remote_url.startswith("http://") or remote_url.startswith("https://")):
            return Response(
                {"error": "Video has no remote source URL to archive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            remote_resp = requests.get(remote_url, stream=True, timeout=(5, 60))
            remote_resp.raise_for_status()
            content = remote_resp.content
        except (requests.ConnectionError, requests.Timeout, requests.RequestException) as err:
            return Response(
                {
                    "error": "Failed to pull remote video stream for archival.",
                    "detail": str(err),
                    "source_url": remote_url,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        file_name = f"evidence_vault_{video_item.id}_{uuid.uuid4().hex[:6]}.mp4"
        video_item.video_file.save(file_name, ContentFile(content), save=True)

        return Response(
            {
                "status": "archived",
                "video_id": video_item.id,
                "file_url": video_item.video_file.url,
                "message": "Video successfully archived into cloud vault.",
            },
            status=status.HTTP_200_OK,
        )


class VideoEvidenceUploadApiView(APIView):
    """
    Multipart MP4 Video Upload API (Backward-Compatible).
    Accepts direct MP4 file uploads from isolated edge nodes.
    Supports HMAC verification or authenticated session.
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        signature_header = (
            request.headers.get("X-Tracker-Signature")
            or request.META.get("HTTP_X_TRACKER_SIGNATURE", "")
        )

        # Authentication check: authenticated user OR valid HMAC signature
        if not request.user.is_authenticated:
            expected_key = get_tracker_secret_key()
            if signature_header:
                event_param = request.POST.get("event_id", "")
                title_param = request.POST.get("title", "")
                sig1 = calculate_hmac_signature(event_param.encode("utf-8"))
                sig2 = calculate_hmac_signature(title_param.encode("utf-8"))
                sig3 = calculate_hmac_signature(b"video_upload")
                valid = (
                    hmac.compare_digest(signature_header, sig1)
                    or hmac.compare_digest(signature_header, sig2)
                    or hmac.compare_digest(signature_header, sig3)
                    or hmac.compare_digest(signature_header, expected_key)
                )
                if not valid:
                    return Response(
                        {"error": "Unauthorized", "detail": "Invalid signature."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            else:
                return Response(
                    {"error": "Unauthorized", "detail": "Authentication or signature required."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        serializer = VideoEvidenceUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Bad Request", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        video_file = data["file"]
        title = data.get("title") or video_file.name
        event_id = data.get("event_id")
        site_id = data.get("site_id")
        site_code = data.get("site_code")
        site_name = data.get("site_name")
        camera_id = data.get("camera_id", "")
        thumbnail_base64 = data.get("thumbnail_base64")

        # Resolve Site Location
        site_obj = None
        if site_id:
            site_obj = Location.objects.filter(id=site_id).first()
        if not site_obj and site_code:
            site_obj = Location.objects.filter(code=site_code).first()
        if not site_obj and site_name:
            site_obj = Location.objects.filter(name__iexact=site_name).first()

        site_label = site_obj.name if site_obj else (site_name or site_code or "Default Site")
        site_slug_part = site_obj.code if site_obj and site_obj.code else (site_code or site_name or "default")
        gallery_slug = slugify(f"security-audit-{site_slug_part}") or "security-audit-default"

        gallery, _ = VideoGallery.objects.get_or_create(
            slug=gallery_slug,
            defaults={
                "name": f"Security Audit - {site_label}",
                "description": f"Surveillance video evidence and journey clips for {site_label}.",
            },
        )

        desc = f"Direct Video Upload | Camera: {camera_id or 'Unknown'}"
        video_item = VideoItem(
            gallery=gallery,
            title=title,
            description=desc,
            source_type=VideoItem.SOURCE_MP4,
            video_file=video_file,
        )

        if thumbnail_base64:
            try:
                if ";base64," in thumbnail_base64:
                    _, b64data = thumbnail_base64.split(";base64,", 1)
                else:
                    b64data = thumbnail_base64
                decoded_thumb = base64.b64decode(b64data)
                thumb_name = f"thumb_up_{uuid.uuid4().hex[:8]}.jpg"
                video_item.thumbnail.save(thumb_name, ContentFile(decoded_thumb), save=False)
            except Exception:
                pass

        video_item.save()

        # Link to SecurityEvent if provided
        if event_id:
            security_event = SecurityEvent.objects.filter(event_id=event_id).first()
            if security_event:
                security_event.video_evidence = video_item
                security_event.metadata["video_uploaded"] = True
                security_event.save(update_fields=["video_evidence", "metadata", "updated_at"])

        SecurityAuditLog.objects.create(
            ip_address=client_ip,
            endpoint=request.path,
            http_method=request.method,
            signature_header=signature_header,
            signature_valid=True,
            event_id=str(event_id) if event_id else f"upload_{video_item.id}",
            status_code=status.HTTP_201_CREATED,
            raw_payload=f"Multipart upload: {title} ({video_file.size} bytes)",
            processed_successfully=True,
        )

        stream_url = f"/api/v1/gallery/stream/{video_item.id}/"
        return Response(
            {
                "status": "success",
                "video_id": video_item.id,
                "gallery_slug": gallery.slug,
                "file_url": video_item.video_file.url,
                "stream_gateway_url": stream_url,
                "event_id": str(event_id) if event_id else None,
                "message": "Video uploaded and registered successfully.",
            },
            status=status.HTTP_201_CREATED,
        )

