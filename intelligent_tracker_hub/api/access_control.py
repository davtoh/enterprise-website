import hmac
import json
import logging
import re

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
    VisitorAccessLog,
)
from ..serializers import (
    SecurityAccessIngestSerializer,
    VisitorAccessLogSerializer,
)
from ..security import verify_hmac_signature, get_tracker_secret_key
from ..notifications import send_visitor_arrival_notification
from ._helpers import (
    decode_base64_image,
    get_signature_header,
    record_audit_log,
    resolve_site_location,
)
from .whitelist_sync import WhitelistDeltaSyncApiView

logger = logging.getLogger(__name__)

__all__ = [
    "WhitelistDeltaSyncApiView",
    "SecurityAccessIngestApiView",
    "VisitorAccessLogViewSet",
]


def _authenticate_access_request(request, signature_header: str) -> Response | None:
    """Verify authenticated session or HMAC signature for gate access ingest."""
    if request.user.is_authenticated:
        return None
    if not signature_header:
        return Response(
            {"error": "Unauthorized", "detail": "HMAC signature or authenticated user required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    expected_key = get_tracker_secret_key()
    valid = (
        verify_hmac_signature(request.body, signature_header)
        or hmac.compare_digest(signature_header, expected_key)
    )
    if valid:
        return None
    record_audit_log(
        request,
        signature_header=signature_header,
        signature_valid=False,
        status_code=status.HTTP_401_UNAUTHORIZED,
        processed_successfully=False,
        error_message="Invalid HMAC signature on gate access event.",
    )
    return Response(
        {"error": "Unauthorized", "detail": "Invalid HMAC signature."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


def _resolve_access_site(data: dict, camera_id: str):
    """Resolve site from payload ID/code, camera fallback, or first Location."""
    site_obj = resolve_site_location(data.get("site_id"), data.get("site_code"))
    if site_obj:
        return site_obj
    cam_obj = Camera.objects.filter(camera_id=camera_id).first()
    if cam_obj and cam_obj.site:
        return cam_obj.site
    return Location.objects.first()


def _resolve_access_contact(data: dict):
    """Match CRM Contact by ID, exact/normalized license plate, or security tag."""
    contact_id = data.get("contact_id")
    license_plate = data.get("license_plate", "").strip()
    security_tag = data.get("security_tag", "").strip()
    if contact_id:
        contact = Contact.objects.filter(id=contact_id).first()
        if contact:
            return contact
    if license_plate:
        contact = Contact.objects.filter(license_plate__iexact=license_plate).first()
        if contact:
            return contact
        norm_input = re.sub(r"[^A-Z0-9]", "", license_plate.upper())
        if norm_input:
            for candidate in Contact.objects.exclude(license_plate=""):
                if candidate.normalized_license_plate == norm_input:
                    return candidate
    if security_tag:
        return Contact.objects.filter(security_tag__iexact=security_tag).first()
    return None


def _evaluate_access_decision(contact, data: dict) -> tuple[bool, str, str]:
    """Determine access_granted, denial_reason, and recognized_identifier."""
    access_granted = data.get("access_granted", True)
    denial_reason = data.get("denial_reason", "")
    if contact:
        recognized_id = contact.full_name
        if contact.security_clearance == SecurityClearance.BANNED:
            return False, denial_reason or _("Banned Entity - Gate Access Denied"), recognized_id
        if not contact.is_pass_valid:
            return False, denial_reason or _("Visitor Pass Expired or Out of Window"), recognized_id
        return access_granted, denial_reason, recognized_id
    recognized_id = (
        data.get("license_plate", "").strip()
        or data.get("security_tag", "").strip()
        or "Unknown Identity"
    )
    if not data.get("access_granted"):
        return False, denial_reason or _("Unrecognized Entity"), recognized_id
    return access_granted, denial_reason, recognized_id


def _decode_access_snapshot(snapshot_base64: str | None):
    """Decode optional base64 snapshot without failing gate access ingestion."""
    if not snapshot_base64:
        return None
    try:
        return decode_base64_image(snapshot_base64, filename_prefix="access")
    except Exception as exc:
        logger.warning("Failed to decode access snapshot base64: %s", exc)
        return None


def _handle_access_side_effects(contact, access_log, site_obj, snapshot_file, data: dict) -> None:
    """Update CRM contact presence/check-out or escalate banned entity attempts."""
    cam_id = access_log.camera_id
    method = access_log.verification_method
    if contact and access_log.access_granted:
        action = contact.check_in if access_log.direction == "ENTRY" else contact.check_out
        verb = "granted" if access_log.direction == "ENTRY" else "exit recorded"
        action(
            location=site_obj,
            verification_method=method,
            gate_camera_id=cam_id,
            notes=f"Gate {verb} via {method}. Camera: {cam_id}.",
        )
        send_visitor_arrival_notification(contact, access_log)
    elif not access_log.access_granted and contact and contact.security_clearance == SecurityClearance.BANNED:
        SecurityEvent.objects.create(
            event_type=SecurityEventType.RESTRICTED_ENTITY,
            site=site_obj,
            camera_id=cam_id,
            timestamp=access_log.timestamp,
            snapshot=snapshot_file,
            severity=SecuritySeverity.CRITICAL,
            metadata={
                "access_id": str(access_log.access_id),
                "contact_id": contact.id,
                "contact_name": contact.full_name,
                "denial_reason": access_log.denial_reason,
                "verification_method": method,
                "confidence": data.get("confidence"),
                "camera_id": cam_id,
                "gate_direction": access_log.direction,
            },
        )
        send_visitor_arrival_notification(contact, access_log)


def _create_access_log(data: dict) -> tuple[VisitorAccessLog, object, object, object]:
    """Resolve site/contact/decision and persist VisitorAccessLog."""
    camera_id = data["camera_id"]
    site_obj = _resolve_access_site(data, camera_id)
    contact = _resolve_access_contact(data)
    access_granted, denial_reason, recognized_id = _evaluate_access_decision(contact, data)
    snapshot_file = _decode_access_snapshot(data.get("snapshot_base64"))
    access_log = VisitorAccessLog.objects.create(
        contact=contact,
        site=site_obj,
        camera_id=camera_id,
        direction=data.get("direction", "ENTRY"),
        verification_method=data.get("verification_method", "face"),
        recognized_identifier=recognized_id,
        confidence=data.get("confidence"),
        access_granted=access_granted,
        denial_reason=denial_reason,
        timestamp=data.get("timestamp") or timezone.now(),
        snapshot=snapshot_file,
        metadata=data.get("metadata", {}),
    )
    return access_log, contact, site_obj, snapshot_file


class SecurityAccessIngestApiView(APIView):
    """
    Ingestion endpoint for physical gate access events (POST /api/v1/security/access/).
    Records entry/exit logs, validates credentials, updates CRM Contact presence to On-Premises,
    creates CRM touchpoint interaction entries, and triggers bilingual host arrival notifications.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        signature_header = get_signature_header(request)
        auth_error = _authenticate_access_request(request, signature_header)
        if auth_error is not None:
            return auth_error

        serializer = SecurityAccessIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Bad Request", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        access_log, contact, site_obj, snapshot_file = _create_access_log(data)
        _handle_access_side_effects(contact, access_log, site_obj, snapshot_file, data)
        record_audit_log(
            request,
            signature_header=signature_header,
            signature_valid=True,
            event_id=str(access_log.access_id),
            status_code=status.HTTP_201_CREATED,
            raw_payload=json.dumps(request.data),
            processed_successfully=True,
        )
        return Response(VisitorAccessLogSerializer(access_log).data, status=status.HTTP_201_CREATED)


class VisitorAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only catalog of physical gate access events.
    """

    queryset = VisitorAccessLog.objects.select_related("contact", "site").all()
    serializer_class = VisitorAccessLogSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["site", "direction", "verification_method", "access_granted"]
    search_fields = ["camera_id", "recognized_identifier", "contact__first_name", "contact__last_name"]
