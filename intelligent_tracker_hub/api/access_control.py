import base64
import hmac
import json
import logging
import re
import uuid

from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Contact, SecurityClearance
from location_management.models import Location
from ..models import (
    Camera,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityAuditLog,
    VisitorAccessLog,
)
from ..serializers import (
    SecurityAccessIngestSerializer,
    VisitorAccessLogSerializer,
)
from ..security import (
    verify_hmac_signature,
    get_client_ip,
    get_tracker_secret_key,
)
from ..notifications import send_visitor_arrival_notification
from .whitelist_sync import WhitelistDeltaSyncApiView

logger = logging.getLogger(__name__)

__all__ = [
    "WhitelistDeltaSyncApiView",
    "SecurityAccessIngestApiView",
    "VisitorAccessLogViewSet",
]


class SecurityAccessIngestApiView(APIView):
    """
    Ingestion endpoint for physical gate access events (POST /api/v1/security/access/).
    Records entry/exit logs, validates credentials, updates CRM Contact presence to On-Premises,
    creates CRM touchpoint interaction entries, and triggers bilingual host arrival notifications.
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

        # HMAC Authentication
        if not request.user.is_authenticated:
            expected_key = get_tracker_secret_key()
            if signature_header:
                valid = (
                    verify_hmac_signature(raw_body, signature_header)
                    or hmac.compare_digest(signature_header, expected_key)
                )
                if not valid:
                    SecurityAuditLog.objects.create(
                        ip_address=client_ip,
                        endpoint=request.path,
                        http_method=request.method,
                        signature_header=signature_header,
                        signature_valid=False,
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        error_message="Invalid HMAC signature on gate access event.",
                        raw_payload=raw_body.decode("utf-8", errors="replace")[:5000],
                        processed_successfully=False,
                    )
                    return Response(
                        {"error": "Unauthorized", "detail": "Invalid HMAC signature."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            else:
                return Response(
                    {"error": "Unauthorized", "detail": "HMAC signature or authenticated user required."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        serializer = SecurityAccessIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Bad Request", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        camera_id = data["camera_id"]
        direction = data.get("direction", "ENTRY")
        verification_method = data.get("verification_method", "face")
        confidence = data.get("confidence")
        timestamp_val = data.get("timestamp") or timezone.now()
        metadata = data.get("metadata", {})
        snapshot_base64 = data.get("snapshot_base64")

        # Resolve Site / Facility
        site_id = data.get("site_id")
        site_code = data.get("site_code")
        site_obj = None
        if site_id:
            site_obj = Location.objects.filter(id=site_id).first()
        if not site_obj and site_code:
            site_obj = Location.objects.filter(code=site_code).first()
        if not site_obj:
            # Fallback to camera's site if camera exists
            cam_obj = Camera.objects.filter(camera_id=camera_id).first()
            if cam_obj and cam_obj.site:
                site_obj = cam_obj.site
            else:
                site_obj = Location.objects.first()

        # Resolve Contact
        contact = None
        contact_id = data.get("contact_id")
        license_plate = data.get("license_plate", "").strip()
        security_tag = data.get("security_tag", "").strip()

        if contact_id:
            contact = Contact.objects.filter(id=contact_id).first()
        if not contact and license_plate:
            norm_input = re.sub(r"[^A-Z0-9]", "", license_plate.upper())
            contact = Contact.objects.filter(license_plate__iexact=license_plate).first()
            if not contact and norm_input:
                for c in Contact.objects.exclude(license_plate=""):
                    if c.normalized_license_plate == norm_input:
                        contact = c
                        break
        if not contact and security_tag:
            contact = Contact.objects.filter(security_tag__iexact=security_tag).first()

        # Determine Access Permission & Denial Reason
        access_granted = data.get("access_granted", True)
        denial_reason = data.get("denial_reason", "")
        recognized_id = ""

        if contact:
            recognized_id = contact.full_name
            if contact.security_clearance == SecurityClearance.BANNED:
                access_granted = False
                denial_reason = denial_reason or _("Banned Entity - Gate Access Denied")
            elif not contact.is_pass_valid:
                access_granted = False
                denial_reason = denial_reason or _("Visitor Pass Expired or Out of Window")
        else:
            recognized_id = license_plate or security_tag or "Unknown Identity"
            if not data.get("access_granted"):
                access_granted = False
                denial_reason = denial_reason or _("Unrecognized Entity")

        # Process snapshot if provided
        snapshot_file = None
        if snapshot_base64:
            try:
                clean_b64 = snapshot_base64
                if "," in clean_b64:
                    clean_b64 = clean_b64.split(",", 1)[1]
                img_data = base64.b64decode(clean_b64)
                snapshot_file = ContentFile(img_data, name=f"access_{uuid.uuid4().hex[:8]}.jpg")
            except Exception as e:
                logger.warning("Failed to decode access snapshot base64: %s", e)

        # Create VisitorAccessLog
        access_log = VisitorAccessLog.objects.create(
            contact=contact,
            site=site_obj,
            camera_id=camera_id,
            direction=direction,
            verification_method=verification_method,
            recognized_identifier=recognized_id,
            confidence=confidence,
            access_granted=access_granted,
            denial_reason=denial_reason,
            timestamp=timestamp_val,
            snapshot=snapshot_file,
            metadata=metadata,
        )

        # Update CRM Contact Presence & Activity Log
        if contact and access_granted:
            if direction == "ENTRY":
                contact.check_in(
                    location=site_obj,
                    verification_method=verification_method,
                    gate_camera_id=camera_id,
                    notes=f"Gate access granted via {verification_method}. Camera: {camera_id}.",
                )
            else:
                contact.check_out(
                    location=site_obj,
                    verification_method=verification_method,
                    gate_camera_id=camera_id,
                    notes=f"Gate exit recorded via {verification_method}. Camera: {camera_id}.",
                )
            # Dispatch bilingual host arrival notification
            send_visitor_arrival_notification(contact, access_log)

        elif not access_granted and (contact and contact.security_clearance == SecurityClearance.BANNED):
            # Escalate critical banned entity attempt to SecurityEvent
            SecurityEvent.objects.create(
                event_type=SecurityEventType.RESTRICTED_ENTITY,
                site=site_obj,
                camera_id=camera_id,
                timestamp=timestamp_val,
                snapshot=snapshot_file,
                severity=SecuritySeverity.CRITICAL,
                metadata={
                    "access_id": str(access_log.access_id),
                    "contact_id": contact.id,
                    "contact_name": contact.full_name,
                    "denial_reason": denial_reason,
                    "verification_method": verification_method,
                    "confidence": confidence,
                    "camera_id": camera_id,
                    "gate_direction": direction,
                },
            )
            # Also dispatch arrival alert notifying security of the intercepted attempt
            send_visitor_arrival_notification(contact, access_log)

        # Audit Log
        SecurityAuditLog.objects.create(
            ip_address=client_ip,
            endpoint=request.path,
            http_method=request.method,
            signature_header=signature_header,
            signature_valid=True,
            event_id=str(access_log.access_id),
            status_code=status.HTTP_201_CREATED,
            raw_payload=json.dumps(request.data),
            processed_successfully=True,
        )

        return Response(
            VisitorAccessLogSerializer(access_log).data,
            status=status.HTTP_201_CREATED,
        )


class VisitorAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only catalog of physical gate access events.
    """

    queryset = VisitorAccessLog.objects.select_related("contact", "site").all()
    serializer_class = VisitorAccessLogSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["site", "direction", "verification_method", "access_granted"]
    search_fields = ["camera_id", "recognized_identifier", "contact__first_name", "contact__last_name"]
