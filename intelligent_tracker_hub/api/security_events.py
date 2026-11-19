import json
import logging
import uuid
from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityAuditLog,
)
from ..serializers import (
    SecurityEventWebhookSerializer,
    SecurityEventSerializer,
    SecurityAuditLogSerializer,
)
from ..security import verify_hmac_signature
from ._helpers import (
    decode_base64_image,
    get_signature_header,
    record_audit_log,
    resolve_site_location,
)

logger = logging.getLogger(__name__)


def _derive_event_severity(data: dict, event_type: str, metadata: dict) -> str:
    """Derive SecuritySeverity from explicit field, metadata, or event type."""
    explicit = data.get("severity")
    if explicit:
        return explicit
    if metadata.get("severity") in SecuritySeverity.values:
        return metadata["severity"]
    if event_type == SecurityEventType.FALL_DETECTED:
        return SecuritySeverity.CRITICAL
    if event_type in (SecurityEventType.INTRUSION, SecurityEventType.RESTRICTED_ENTITY):
        return SecuritySeverity.HIGH
    if event_type in (SecurityEventType.OCCUPANCY_THRESHOLD, SecurityEventType.LOITERING):
        return SecuritySeverity.MEDIUM
    return SecuritySeverity.LOW


def _verify_webhook_request(request, signature_header: str) -> Response | None:
    """Validate HMAC-SHA256 signature on incoming security event webhook."""
    if verify_hmac_signature(request.body, signature_header):
        return None
    record_audit_log(
        request,
        signature_header=signature_header,
        signature_valid=False,
        status_code=status.HTTP_401_UNAUTHORIZED,
        processed_successfully=False,
        error_message="Missing or invalid X-Tracker-Signature HMAC signature.",
    )
    return Response(
        {
            "error": "Unauthorized",
            "detail": "Missing or invalid X-Tracker-Signature HMAC-SHA256 signature.",
        },
        status=status.HTTP_401_UNAUTHORIZED,
    )


def _persist_security_event(data: dict) -> SecurityEvent:
    """Build and save SecurityEvent including optional base64 snapshot evidence."""
    event_id = data.get("event_id") or uuid.uuid4()
    event_type = data["event_type"]
    metadata = data.get("metadata") or {}
    security_event = SecurityEvent(
        event_id=event_id,
        event_type=event_type,
        site=resolve_site_location(data.get("site_id"), data.get("site_code")),
        camera_id=data["camera_id"],
        timestamp=data.get("timestamp") or timezone.now(),
        metadata=metadata,
        severity=_derive_event_severity(data, event_type, metadata),
    )
    snapshot_base64 = data.get("snapshot_base64")
    if snapshot_base64:
        try:
            content_file = decode_base64_image(snapshot_base64)
            security_event.snapshot.save(f"{event_id}.jpg", content_file, save=False)
        except Exception as exc:
            metadata["snapshot_decode_error"] = str(exc)
    security_event.save()
    return security_event


class SecurityEventWebhookApiView(APIView):
    """
    Webhook receiver endpoint for edge AI vision nodes (intelligent-tracker).
    Requires a valid HMAC-SHA256 signature in the X-Tracker-Signature HTTP header.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        signature_header = get_signature_header(request)
        auth_error = _verify_webhook_request(request, signature_header)
        if auth_error is not None:
            return auth_error

        serializer = SecurityEventWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            record_audit_log(
                request,
                signature_header=signature_header,
                signature_valid=True,
                status_code=status.HTTP_400_BAD_REQUEST,
                processed_successfully=False,
                error_message=json.dumps(serializer.errors),
            )
            return Response({"error": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        security_event = _persist_security_event(serializer.validated_data)
        record_audit_log(
            request,
            signature_header=signature_header,
            signature_valid=True,
            event_id=str(security_event.event_id),
            status_code=status.HTTP_201_CREATED,
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

