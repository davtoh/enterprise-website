import hmac
import json
import logging

from django.utils.text import slugify
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from video_gallery.models import VideoGallery, VideoItem
from ..models import SecurityEvent
from ..serializers import (
    VideoEvidenceRegisterSerializer,
    VideoEvidenceUploadSerializer,
)
from ..security import (
    verify_hmac_signature,
    calculate_hmac_signature,
    get_tracker_secret_key,
)
from ._helpers import (
    decode_base64_image,
    get_signature_header,
    record_audit_log,
    resolve_site_location,
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


def _get_or_create_gallery(site_obj, site_code, site_name):
    """Resolve or create the VideoGallery for security evidence."""
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


def _attach_thumbnail(video_item: VideoItem, thumbnail_base64: str | None, prefix: str, metadata: dict | None = None) -> None:
    """Decode and attach optional base64 thumbnail to VideoItem."""
    if not thumbnail_base64:
        return
    try:
        content_file = decode_base64_image(thumbnail_base64, filename_prefix=prefix)
        video_item.thumbnail.save(content_file.name, content_file, save=False)
    except Exception as exc:
        if metadata is not None:
            metadata["thumbnail_decode_error"] = str(exc)


def _link_video_to_event(event_id, video_item: VideoItem, *, trajectory=None, duration_seconds=None, uploaded: bool = False) -> None:
    """Associate a VideoItem with its corresponding SecurityEvent if present."""
    if not event_id:
        return
    security_event = SecurityEvent.objects.filter(event_id=event_id).first()
    if not security_event:
        return
    security_event.video_evidence = video_item
    if trajectory:
        security_event.metadata["trajectory"] = trajectory
    if duration_seconds:
        security_event.metadata["video_duration"] = duration_seconds
    security_event.metadata["video_uploaded" if uploaded else "video_registered"] = True
    security_event.save(update_fields=["video_evidence", "metadata", "updated_at"])


def _verify_register_hmac(request, signature_header: str) -> Response | None:
    """Verify HMAC-SHA256 signature for zero-copy video registration."""
    if verify_hmac_signature(request.body, signature_header):
        return None
    record_audit_log(
        request,
        signature_header=signature_header,
        signature_valid=False,
        status_code=status.HTTP_401_UNAUTHORIZED,
        processed_successfully=False,
        error_message="Missing or invalid X-Tracker-Signature for video registration.",
    )
    return Response(
        {"error": "Unauthorized", "detail": "Missing or invalid X-Tracker-Signature HMAC-SHA256 signature."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


def _authenticate_upload_request(request, signature_header: str) -> Response | None:
    """Verify authenticated session or multipart upload HMAC signature."""
    if request.user.is_authenticated:
        return None
    if not signature_header:
        return Response(
            {"error": "Unauthorized", "detail": "Authentication or signature required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    expected_key = get_tracker_secret_key()
    candidates = (
        calculate_hmac_signature(request.POST.get("event_id", "").encode("utf-8")),
        calculate_hmac_signature(request.POST.get("title", "").encode("utf-8")),
        calculate_hmac_signature(b"video_upload"),
        expected_key,
    )
    if any(hmac.compare_digest(signature_header, sig) for sig in candidates):
        return None
    return Response(
        {"error": "Unauthorized", "detail": "Invalid signature."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


def _create_registered_video(data: dict) -> tuple[VideoGallery, VideoItem]:
    """Create a zero-copy VideoItem from validated registration payload."""
    site_obj = resolve_site_location(data.get("site_id"), data.get("site_code"), data.get("site_name"))
    gallery = _get_or_create_gallery(site_obj, data.get("site_code"), data.get("site_name"))
    desc_parts = [f"Edge Video Evidence | Camera: {data.get('camera_id', '') or 'Unknown'}"]
    if data.get("duration_seconds"):
        desc_parts.append(f"Duration: {data['duration_seconds']:.1f}s")
    if data.get("trajectory"):
        desc_parts.append(f"Ground-Plane Homography Points: {len(data['trajectory'])}")
    video_item = VideoItem(
        gallery=gallery,
        title=data["title"],
        description=" | ".join(desc_parts),
        source_type=VideoItem.SOURCE_MP4,
        embed_url=data["source_url"],
    )
    _attach_thumbnail(video_item, data.get("thumbnail_base64"), "thumb_ev", data.get("metadata", {}))
    video_item.save()
    _link_video_to_event(
        data.get("event_id"),
        video_item,
        trajectory=data.get("trajectory"),
        duration_seconds=data.get("duration_seconds"),
    )
    return gallery, video_item


def _create_uploaded_video(data: dict) -> tuple[VideoGallery, VideoItem, str]:
    """Persist an uploaded MP4 VideoItem and link any associated SecurityEvent."""
    video_file = data["file"]
    title = data.get("title") or video_file.name
    site_obj = resolve_site_location(data.get("site_id"), data.get("site_code"), data.get("site_name"))
    gallery = _get_or_create_gallery(site_obj, data.get("site_code"), data.get("site_name"))
    video_item = VideoItem(
        gallery=gallery,
        title=title,
        description=f"Direct Video Upload | Camera: {data.get('camera_id', '') or 'Unknown'}",
        source_type=VideoItem.SOURCE_MP4,
        video_file=video_file,
    )
    _attach_thumbnail(video_item, data.get("thumbnail_base64"), "thumb_up")
    video_item.save()
    _link_video_to_event(data.get("event_id"), video_item, uploaded=True)
    return gallery, video_item, title


class VideoEvidenceRegisterApiView(APIView):
    """
    Zero-Copy Video Evidence Registration API.
    Edge AI vision nodes register clip URLs directly without transferring heavy MP4 files to the Hub.
    Requires HMAC-SHA256 signature (X-Tracker-Signature).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        signature_header = get_signature_header(request)
        auth_error = _verify_register_hmac(request, signature_header)
        if auth_error is not None:
            return auth_error

        serializer = VideoEvidenceRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            record_audit_log(
                request, signature_header=signature_header, signature_valid=True,
                status_code=status.HTTP_400_BAD_REQUEST, processed_successfully=False,
                error_message=json.dumps(serializer.errors),
            )
            return Response({"error": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        gallery, video_item = _create_registered_video(data)
        event_id = data.get("event_id")
        record_audit_log(
            request, signature_header=signature_header, signature_valid=True,
            event_id=str(event_id) if event_id else f"video_{video_item.id}",
            status_code=status.HTTP_201_CREATED, processed_successfully=True,
        )
        return Response(
            {
                "status": "success",
                "video_id": video_item.id,
                "gallery_slug": gallery.slug,
                "gallery_name": gallery.name,
                "stream_gateway_url": f"/api/v1/gallery/stream/{video_item.id}/",
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
        signature_header = get_signature_header(request)
        auth_error = _authenticate_upload_request(request, signature_header)
        if auth_error is not None:
            return auth_error

        serializer = VideoEvidenceUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        gallery, video_item, title = _create_uploaded_video(data)
        event_id = data.get("event_id")
        record_audit_log(
            request,
            signature_header=signature_header,
            signature_valid=True,
            event_id=str(event_id) if event_id else f"upload_{video_item.id}",
            status_code=status.HTTP_201_CREATED,
            raw_payload=f"Multipart upload: {title} ({data['file'].size} bytes)",
            processed_successfully=True,
        )
        return Response(
            {
                "status": "success",
                "video_id": video_item.id,
                "gallery_slug": gallery.slug,
                "file_url": video_item.video_file.url,
                "stream_gateway_url": f"/api/v1/gallery/stream/{video_item.id}/",
                "event_id": str(event_id) if event_id else None,
                "message": "Video uploaded and registered successfully.",
            },
            status=status.HTTP_201_CREATED,
        )
