import base64
import json
import uuid
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import SecurityEvent, SecurityEventType, SecuritySeverity, SecurityAuditLog
from .serializers import (
    SecurityEventWebhookSerializer,
    SecurityEventSerializer,
    SecurityAuditLogSerializer,
)
from .security import verify_hmac_signature, get_client_ip
from location_management.models import Location


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
