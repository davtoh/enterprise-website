import json
from django.urls import reverse

from crm.models import InteractionLog, InteractionType, PresenceStatus
from intelligent_tracker_hub.models import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    VisitorAccessLog,
    AccessDirection,
    VerificationMethod,
)
from intelligent_tracker_hub.security import (
    calculate_hmac_signature,
    get_tracker_secret_key,
)
from intelligent_tracker_hub.notifications import send_visitor_arrival_notification
from .test_whitelist_sync import (
    test_crm_contact_physical_security_credentials_and_methods,
    test_visitor_access_log_model,
    test_whitelist_delta_sync_api_unauthorized,
    test_whitelist_delta_sync_api_success_and_etag,
    test_whitelist_delta_sync_api_filters_expired_passes_and_marks_banned,
    test_whitelist_delta_sync_api_since_parameter,
)

__all__ = [
    "test_crm_contact_physical_security_credentials_and_methods",
    "test_visitor_access_log_model",
    "test_whitelist_delta_sync_api_unauthorized",
    "test_whitelist_delta_sync_api_success_and_etag",
    "test_whitelist_delta_sync_api_filters_expired_passes_and_marks_banned",
    "test_whitelist_delta_sync_api_since_parameter",
    "test_security_access_ingest_api_unauthorized",
    "test_security_access_ingest_entry_granted_and_presence_update",
    "test_security_access_ingest_exit_and_presence_update",
    "test_security_access_ingest_by_license_plate_anpr",
    "test_security_access_ingest_banned_contact_escalates_to_security_event",
    "test_visitor_arrival_notification_service",
    "test_visitor_access_catalog_viewset",
]


def test_security_access_ingest_api_unauthorized(client):
    url = reverse("intelligent_tracker_api:security_access")
    resp = client.post(
        url,
        data={"camera_id": "cam-gate-01"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_security_access_ingest_entry_granted_and_presence_update(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    contact = test_contacts[0]  # Sarah Connor (VIP)

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-gate-entry-01",
        "contact_id": contact.id,
        "direction": "ENTRY",
        "verification_method": "face",
        "confidence": 0.99,
        "access_granted": True,
        "metadata": {"turnstile": 2},
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_granted"] is True
    assert data["direction"] == "ENTRY"
    assert data["contact"] == contact.id

    # Verify contact presence in DB
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.ON_PREMISES
    assert contact.last_seen_location == test_location

    # Verify InteractionLog
    interaction = InteractionLog.objects.filter(contact=contact, interaction_type=InteractionType.SECURITY_ACCESS).first()
    assert interaction is not None
    assert "cam-gate-entry-01" in interaction.details


def test_security_access_ingest_exit_and_presence_update(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    contact = test_contacts[0]
    contact.presence_status = PresenceStatus.ON_PREMISES
    contact.save()

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-gate-exit-01",
        "contact_id": contact.id,
        "direction": "EXIT",
        "verification_method": "face",
        "confidence": 0.97,
        "access_granted": True,
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.OFF_PREMISES


def test_security_access_ingest_by_license_plate_anpr(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    contact = test_contacts[1]  # Kyle Reese (CA-123-KLR)

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-anpr-gate",
        "license_plate": "CA 123 KLR",  # Spaced format
        "direction": "ENTRY",
        "verification_method": "plate",
        "confidence": 0.94,
        "access_granted": True,
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["contact"] == contact.id
    contact.refresh_from_db()
    assert contact.presence_status == PresenceStatus.ON_PREMISES


def test_security_access_ingest_banned_contact_escalates_to_security_event(client, test_contacts, test_location):
    url = reverse("intelligent_tracker_api:security_access")
    secret = get_tracker_secret_key()
    banned_contact = test_contacts[3]  # Miles Dyson (BANNED)

    payload = {
        "site_id": test_location.id,
        "camera_id": "cam-gate-01",
        "contact_id": banned_contact.id,
        "direction": "ENTRY",
        "verification_method": "face",
        "confidence": 0.96,
        "access_granted": True,  # Edge might optimistically request, hub must deny!
    }
    raw_json = json.dumps(payload).encode("utf-8")
    sig = calculate_hmac_signature(raw_json, secret=secret)

    resp = client.post(
        url,
        data=raw_json,
        content_type="application/json",
        HTTP_X_TRACKER_SIGNATURE=sig,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_granted"] is False
    assert "Banned" in data["denial_reason"]

    # Contact must remain OFF_PREMISES
    banned_contact.refresh_from_db()
    assert banned_contact.presence_status == PresenceStatus.OFF_PREMISES

    # Verify a CRITICAL SecurityEvent was automatically created!
    sec_event = SecurityEvent.objects.filter(
        event_type=SecurityEventType.RESTRICTED_ENTITY,
        severity=SecuritySeverity.CRITICAL,
    ).first()
    assert sec_event is not None
    assert sec_event.metadata.get("contact_id") == banned_contact.id


def test_visitor_arrival_notification_service(db, test_contacts, test_location, mailoutbox):
    contact = test_contacts[0]
    log = VisitorAccessLog.objects.create(
        contact=contact,
        site=test_location,
        camera_id="cam-gate-01",
        direction=AccessDirection.ENTRY,
        verification_method=VerificationMethod.FACE,
        access_granted=True,
    )

    sent = send_visitor_arrival_notification(contact, log)
    assert sent is True
    assert len(mailoutbox) == 1
    email = mailoutbox[0]
    assert "Sarah Connor" in email.subject
    assert "[ENGLISH]" in email.body
    assert "[ESPAÑOL]" in email.body
    assert "NOTIFICACIÓN DE ACCESO" in email.body.upper()


def test_visitor_access_catalog_viewset(client, auth_user, test_contacts, test_location):
    client.force_login(auth_user)
    VisitorAccessLog.objects.create(
        contact=test_contacts[0],
        site=test_location,
        camera_id="cam-catalog-01",
        direction=AccessDirection.ENTRY,
        verification_method=VerificationMethod.FACE,
        access_granted=True,
    )

    url = "/api/v1/security/access/catalog/"
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1
