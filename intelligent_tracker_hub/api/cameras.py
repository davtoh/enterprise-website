import hmac
import json
import logging
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from location_management.models import Location
from ..models import Camera, CameraStatus, SecurityAuditLog
from ..serializers import CameraSerializer, CameraHeartbeatSerializer
from ..security import verify_hmac_signature, get_client_ip, get_tracker_secret_key

logger = logging.getLogger(__name__)

__all__ = [
    "CameraHeartbeatApiView",
    "CameraViewSet",
]


class CameraHeartbeatApiView(APIView):
    """
    Heartbeat receiver endpoint for Edge AI camera nodes.
    Accepts HMAC-SHA256 signature (X-Tracker-Signature) or authenticated session.
    Registers or updates camera connection status and telemetry metrics.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        signature_header = (
            request.headers.get("X-Tracker-Signature")
            or request.META.get("HTTP_X_TRACKER_SIGNATURE", "")
        )

        # Check authentication: authenticated user OR valid HMAC signature
        if not request.user.is_authenticated:
            expected_key = get_tracker_secret_key()
            if signature_header:
                valid = verify_hmac_signature(
                    request.body, signature_header
                ) or hmac.compare_digest(signature_header, expected_key)
                if not valid:
                    return Response(
                        {"error": "Unauthorized", "detail": "Invalid HMAC signature."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            else:
                return Response(
                    {
                        "error": "Unauthorized",
                        "detail": "HMAC signature or authenticated user required.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        serializer = CameraHeartbeatSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Bad Request", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        camera_id = data["camera_id"]
        status_val = data.get("status", CameraStatus.ONLINE)
        fps = data.get("fps", 30)
        resolution = data.get("resolution", "1920x1080")
        stream_url = data.get("stream_url", "")
        name = data.get("name") or f"Camera {camera_id}"
        site_id = data.get("site_id")
        site_code = data.get("site_code")
        metadata = data.get("metadata", {})

        site_obj = None
        if site_id:
            site_obj = Location.objects.filter(id=site_id).first()
        if not site_obj and site_code:
            site_obj = Location.objects.filter(code=site_code).first()

        camera, created = Camera.objects.get_or_create(
            camera_id=camera_id,
            defaults={
                "name": name,
                "site": site_obj,
                "stream_url": stream_url,
                "status": status_val,
                "fps": fps,
                "resolution": resolution,
                "last_heartbeat": timezone.now(),
                "metadata": metadata,
            },
        )

        if not created:
            camera.status = status_val
            camera.fps = fps
            camera.resolution = resolution
            camera.last_heartbeat = timezone.now()
            if stream_url:
                camera.stream_url = stream_url
            if site_obj:
                camera.site = site_obj
            if metadata:
                camera.metadata.update(metadata)
            camera.save()

        SecurityAuditLog.objects.create(
            ip_address=client_ip,
            endpoint=request.path,
            http_method=request.method,
            signature_header=signature_header,
            signature_valid=True,
            event_id=f"heartbeat_{camera_id}",
            status_code=status.HTTP_200_OK,
            raw_payload=json.dumps(request.data),
            processed_successfully=True,
        )

        return Response(
            {
                "status": "recorded",
                "camera_id": camera.camera_id,
                "camera_name": camera.name,
                "camera_status": camera.status,
                "is_alive": camera.is_alive,
                "last_heartbeat": camera.last_heartbeat.isoformat(),
                "stream_proxy_url": camera.get_stream_proxy_url(),
            },
            status=status.HTTP_200_OK,
        )


class CameraViewSet(viewsets.ModelViewSet):
    """
    CRUD API for registered Cameras in the Enterprise Security Hub.
    """

    queryset = Camera.objects.select_related("site").all()
    serializer_class = CameraSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["site", "status", "is_active"]
    search_fields = ["camera_id", "name", "stream_url"]

