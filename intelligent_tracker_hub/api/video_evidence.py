import base64
import hmac
import json
import logging
import uuid

from django.core.files.base import ContentFile
from django.utils.text import slugify
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from location_management.models import Location
from video_gallery.models import VideoGallery, VideoItem
from ..models import SecurityEvent, SecurityAuditLog
from ..serializers import (
    VideoEvidenceRegisterSerializer,
    VideoEvidenceUploadSerializer,
)
from ..security import (
    verify_hmac_signature,
    get_client_ip,
    calculate_hmac_signature,
    get_tracker_secret_key,
)
from .video_streaming import (
    VideoEvidenceStreamGatewayApiView,
    VideoEvidenceArchiveApiView,
)

logger = logging.getLogger(__name__)

__all__ = [
    "VideoEvidenceRegisterApiView",
    "VideoEvidenceUploadApiView",
    "VideoEvidenceStreamGatewayApiView",
    "VideoEvidenceArchiveApiView",
]


def _resolve_site(site_id=None, site_code=None, site_name=None):
    """Helper to resolve Location site from ID, code, or name."""
    site_obj = None
    if site_id:
        site_obj = Location.objects.filter(id=site_id).first()
    if not site_obj and site_code:
        site_obj = Location.objects.filter(code=site_code).first()
    if not site_obj and site_name:
        site_obj = Location.objects.filter(name__iexact=site_name).first()
    return site_obj


def _get_or_create_gallery(site_obj, site_code, site_name):
    """Helper to resolve or create the VideoGallery for security evidence."""
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
    return gallery


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

        # 3. Resolve Site Location & Gallery
        site_obj = _resolve_site(site_id, site_code, site_name)
        gallery = _get_or_create_gallery(site_obj, site_code, site_name)

        # 4. Build Description with camera, duration, and homography telemetry
        desc_parts = [f"Edge Video Evidence | Camera: {camera_id or 'Unknown'}"]
        if duration_seconds:
            desc_parts.append(f"Duration: {duration_seconds:.1f}s")
        if trajectory:
            desc_parts.append(f"Ground-Plane Homography Points: {len(trajectory)}")
        description = " | ".join(desc_parts)

        # 5. Create VideoItem (source_type=mp4, embed_url=source_url, zero disk copy)
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

        # 6. Associate with SecurityEvent if event_id provided
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

        # 7. Record Audit Log
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

        # Resolve Site Location & Gallery
        site_obj = _resolve_site(site_id, site_code, site_name)
        gallery = _get_or_create_gallery(site_obj, site_code, site_name)

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
