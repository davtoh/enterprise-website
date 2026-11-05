import time
import urllib.parse
from django.urls import reverse
from django.utils import timezone

from crm.models import (
    Contact,
    SecurityClearance,
    PresenceStatus,
    InteractionLog,
    InteractionType,
)
from intelligent_tracker_hub.models import (
    VisitorAccessLog,
    AccessDirection,
    VerificationMethod,
)
from intelligent_tracker_hub.security import (
    calculate_hmac_signature,
    get_tracker_secret_key,
)

__all__ = [
    "test_crm_contact_physical_security_credentials_and_methods",
    "test_visitor_access_log_model",
    "test_whitelist_delta_sync_api_unauthorized",
    "test_whitelist_delta_sync_api_success_and_etag",
    "test_whitelist_delta_sync_api_filters_expired_passes_and_marks_banned",
    "test_whitelist_delta_sync_api_since_parameter",
]


def test_crm_contact_physical_security_credentials_and_methods(db, test_location):
    contact = Contact.objects.create(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        security_clearance=SecurityClearance.VIP,
        license_plate="abc-1234",
        security_tag="secure-zone-a",
        valid_from=timezone.now() - timezone.timedelta(hours=1),
        valid_until=timezone.now() + timezone.timedelta(days=1),
    )

    assert contact.normalized_license_plate == "ABC1234"
    assert contact.is_pass_valid is True
    assert contact.presence_status == PresenceStatus.OFF_PREMISES
    assert contact.presence_badge_class == "secondary"
    assert "warning" in contact.clearance_badge_class

    # Test check_in
    contact.check_in(location=test_location, verification_method="face", gate_camera_id="cam-gate-01")
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.ON_PREMISES
    assert contact.presence_badge_class == "success"
    assert contact.last_seen_location == test_location
    assert contact.last_seen_at is not None

    # Verify InteractionLog
    interaction = InteractionLog.objects.filter(contact=contact, interaction_type=InteractionType.SECURITY_ACCESS).first()
    assert interaction is not None
    assert "Entry" in interaction.summary
    assert "Face" in interaction.summary

    # Test check_out
    contact.check_out(location=test_location, verification_method="plate", gate_camera_id="cam-gate-01")
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.OFF_PREMISES

    # Test pass validity window
    contact.valid_until = timezone.now() - timezone.timedelta(minutes=5)
    contact.save()
    assert contact.is_pass_valid is False

    # Banned contact is always invalid
    contact.valid_until = timezone.now() + timezone.timedelta(days=10)
    contact.security_clearance = SecurityClearance.BANNED
    contact.save()
    assert contact.is_pass_valid is False


def test_visitor_access_log_model(db, test_location):
    contact = Contact.objects.create(
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        security_clearance=SecurityClearance.STAFF,
    )
    log = VisitorAccessLog.objects.create(
        contact=contact,
        site=test_location,
        camera_id="cam-north-01",
        direction=AccessDirection.ENTRY,
        verification_method=VerificationMethod.FACE,
        recognized_identifier=contact.full_name,
        confidence=0.98,
        access_granted=True,
    )

    assert str(log.access_id) in str(log) or "Alice Smith" in str(log)
    assert log.status_badge_class == "success"
    assert log.access_granted is True


def test_whitelist_delta_sync_api_unauthorized(client):
    url = reverse("intelligent_tracker_api:security_whitelist")
    resp = client.get(url)
    assert resp.status_code == 401


def test_whitelist_delta_sync_api_success_and_etag(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_whitelist")
    secret = get_tracker_secret_key()
    sig = calculate_hmac_signature(b"", secret=secret)

    # 1. Initial full fetch
    resp = client.get(
        f"{url}?site_id={test_location.id}",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "whitelist" in data
    assert "version_hash" in data
    assert "revoked_ids" in data
    assert "ETag" in resp.headers

    etag = resp.headers["ETag"]
    assert len(etag) > 10

    # 2. Re-request with matching If-None-Match header -> 304 Not Modified
    resp_304 = client.get(
        f"{url}?site_id={test_location.id}",
        HTTP_X_TRACKER_SIGNATURE=sig,
        HTTP_IF_NONE_MATCH=etag,
    )
    assert resp_304.status_code == 304
    assert resp_304.content == b""


def test_whitelist_delta_sync_api_filters_expired_passes_and_marks_banned(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_whitelist")
    secret = get_tracker_secret_key()
    sig = calculate_hmac_signature(b"", secret=secret)

    resp = client.get(
        f"{url}?site_id={test_location.id}",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 200
    data = resp.json()

    whitelist = data["whitelist"]
    contact_emails = [c["email"] for c in whitelist]

    # Active VIP and Contractor are in whitelist
    assert "sconnor@example.com" in contact_emails
    assert "kreese@example.com" in contact_emails

    # Expired Visitor pass is EXCLUDED from active whitelist
    assert "expired@example.com" not in contact_emails

    # Banned contact is included with is_banned: true so edge immediately denies
    banned_item = next((c for c in whitelist if c["email"] == "mdyson@example.com"), None)
    assert banned_item is not None
    assert banned_item["is_banned"] is True
    assert banned_item["security_clearance"] == "BANNED"

    # Expired contact ID must be in revoked_ids
    expired_contact = next(c for c in test_contacts if c.email == "expired@example.com")
    assert expired_contact.id in data["revoked_ids"]


def test_whitelist_delta_sync_api_since_parameter(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_whitelist")
    secret = get_tracker_secret_key()
    sig = calculate_hmac_signature(b"", secret=secret)

    time.sleep(0.02)
    cutoff = timezone.now()
    time.sleep(0.02)

    # Update only one contact
    c1 = test_contacts[0]
    c1.security_tag = "new-updated-tag"
    c1.save()

    encoded_since = urllib.parse.quote(cutoff.isoformat())
    resp = client.get(
        f"{url}?since={encoded_since}",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["whitelist"]) == 1
    assert data["whitelist"][0]["contact_id"] == c1.id
    assert data["whitelist"][0]["security_tag"] == "new-updated-tag"

