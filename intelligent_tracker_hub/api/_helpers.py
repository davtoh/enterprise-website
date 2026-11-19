import base64
import uuid

from django.core.files.base import ContentFile

from location_management.models import Location
from ..models import SecurityAuditLog


def get_signature_header(request) -> str:
    """Extract X-Tracker-Signature header from request headers or META."""
    return (
        request.headers.get("X-Tracker-Signature")
        or request.META.get("HTTP_X_TRACKER_SIGNATURE", "")
    )


def record_audit_log(
    request,
    *,
    signature_header: str,
    signature_valid: bool,
    status_code: int,
    processed_successfully: bool,
    raw_payload: str | None = None,
    error_message: str = "",
    event_id: str = "",
) -> None:
    """Persist a SecurityAuditLog entry for edge webhook and ingest requests."""
    from ..security import get_client_ip

    payload = (
        raw_payload
        if raw_payload is not None
        else request.body.decode("utf-8", errors="replace")[:5000]
    )
    SecurityAuditLog.objects.create(
        ip_address=get_client_ip(request),
        endpoint=request.path,
        http_method=request.method,
        signature_header=signature_header,
        signature_valid=signature_valid,
        event_id=event_id,
        status_code=status_code,
        error_message=error_message,
        raw_payload=payload,
        processed_successfully=processed_successfully,
    )


def decode_base64_image(b64_value: str, filename_prefix: str = "img") -> ContentFile:
    """Decode a raw or data-URI base64 image string into a Django ContentFile."""
    clean_b64 = b64_value.split(",", 1)[1] if "," in b64_value else b64_value
    decoded_bytes = base64.b64decode(clean_b64)
    return ContentFile(decoded_bytes, name=f"{filename_prefix}_{uuid.uuid4().hex[:8]}.jpg")


def resolve_site_location(site_id=None, site_code=None, site_name=None):
    """Resolve Location site from ID, code, or case-insensitive name."""
    site_obj = None
    if site_id:
        site_obj = Location.objects.filter(id=site_id).first()
    if not site_obj and site_code:
        site_obj = Location.objects.filter(code=site_code).first()
    if not site_obj and site_name:
        site_obj = Location.objects.filter(name__iexact=site_name).first()
    return site_obj
