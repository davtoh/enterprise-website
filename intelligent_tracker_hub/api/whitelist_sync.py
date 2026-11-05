import hashlib
import hmac
import logging
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Contact, SecurityClearance
from location_management.models import Location
from ..serializers import CRMContactWhitelistItemSerializer
from ..security import verify_hmac_signature, get_client_ip, get_tracker_secret_key

logger = logging.getLogger(__name__)

__all__ = ["WhitelistDeltaSyncApiView"]


class WhitelistDeltaSyncApiView(APIView):
    """
    High-Performance CRM Contact Whitelist Delta-Sync API for edge AI vision nodes.
    Supports HTTP ETag (If-None-Match), returning 304 Not Modified with 0 bytes if credentials have not changed.
    Supports ?since=<iso_timestamp> for incremental updates.
    Automatically filters out expired temporary visitor passes and handles banned entities.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        signature_header = (
            request.headers.get("X-Tracker-Signature")
            or request.META.get("HTTP_X_TRACKER_SIGNATURE", "")
        )

        # Authenticate via active Django session OR valid HMAC signature
        if not request.user.is_authenticated:
            expected_key = get_tracker_secret_key()
            if signature_header:
                valid = (
                    verify_hmac_signature(request.body, signature_header)
                    or verify_hmac_signature(b"", signature_header)
                    or verify_hmac_signature(request.META.get("QUERY_STRING", "").encode("utf-8"), signature_header)
                    or hmac.compare_digest(signature_header, expected_key)
                )
                if not valid:
                    return Response(
                        {"error": "Unauthorized", "detail": "Invalid HMAC signature."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            else:
                return Response(
                    {"error": "Unauthorized", "detail": "HMAC signature or authenticated user required."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        site_id = request.GET.get("site_id")
        site_code = request.GET.get("site_code")
        since_param = request.GET.get("since")

        site_obj = None
        if site_id:
            try:
                site_obj = Location.objects.filter(id=int(site_id)).first()
            except (ValueError, TypeError):
                pass
        if not site_obj and site_code:
            site_obj = Location.objects.filter(code=site_code).first()

        now = timezone.now()

        # Query all active or clearance-bearing contacts
        qs = Contact.objects.select_related("company").all()

        # Filter out expired passes: if valid_until is set and is in the past, pass is expired
        # Note: Banned contacts are kept so edge nodes recognize and intercept them immediately
        qs = qs.exclude(
            ~Q(security_clearance=SecurityClearance.BANNED),
            valid_until__isnull=False,
            valid_until__lt=now,
        )

        # Filter not-yet-valid passes
        qs = qs.exclude(
            ~Q(security_clearance=SecurityClearance.BANNED),
            valid_from__isnull=False,
            valid_from__gt=now,
        )

        # Incremental sync with ?since=
        if since_param:
            try:
                since_clean = since_param.strip().replace(" ", "+").replace("Z", "+00:00")
                since_dt = parse_datetime(since_clean)
                if not since_dt:
                    since_dt = timezone.datetime.fromisoformat(since_clean)
                if timezone.is_naive(since_dt):
                    since_dt = timezone.make_aware(since_dt, timezone.utc)
                qs = qs.filter(updated_at__gte=since_dt)
            except Exception as e:
                logger.warning("Invalid ?since timestamp format '%s': %s", since_param, e)

        contacts = list(qs.order_by("id"))

        # Compute deterministic content digest for ETag
        hash_input = []
        for c in contacts:
            ts = c.updated_at.isoformat() if c.updated_at else ""
            hash_input.append(f"{c.id}:{ts}:{c.security_clearance}:{c.license_plate}")
        version_hash = hashlib.sha256(";".join(hash_input).encode("utf-8")).hexdigest()
        etag_val = f'"{version_hash}"'

        # Check If-None-Match header for HTTP 304 Not Modified
        if_none_match = request.headers.get("If-None-Match") or request.META.get("HTTP_IF_NONE_MATCH", "")
        if if_none_match and if_none_match.strip() == etag_val:
            response = HttpResponse(status=status.HTTP_304_NOT_MODIFIED)
            response["ETag"] = etag_val
            response["Cache-Control"] = "private, must-revalidate, max-age=10"
            return response

        # Query revoked or banned IDs for edge purge / deny list
        banned_ids = list(Contact.objects.filter(security_clearance=SecurityClearance.BANNED).values_list("id", flat=True))
        expired_ids = list(Contact.objects.filter(valid_until__isnull=False, valid_until__lt=now).values_list("id", flat=True))
        revoked_ids = list(set(banned_ids + expired_ids))

        serialized = CRMContactWhitelistItemSerializer(contacts, many=True).data

        data = {
            "site_id": site_obj.id if site_obj else None,
            "site_code": site_obj.code if site_obj else (site_code or ""),
            "version_hash": version_hash,
            "server_time": now.isoformat(),
            "total_count": len(serialized),
            "whitelist": serialized,
            "revoked_ids": revoked_ids,
        }

        response = Response(data, status=status.HTTP_200_OK)
        response["ETag"] = etag_val
        response["Cache-Control"] = "private, must-revalidate, max-age=10"
        return response

