import pytest
from django.urls import reverse

from intelligent_tracker_hub.models import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
)
from plugin_registry import registry


@pytest.mark.django_db
def test_security_catalog_and_stats_api(client, test_location):
    e1 = SecurityEvent.objects.create(
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-01",
        severity=SecuritySeverity.HIGH,
    )
    e2 = SecurityEvent.objects.create(
        event_type=SecurityEventType.FALL_DETECTED,
        site=test_location,
        camera_id="cam-02",
        severity=SecuritySeverity.CRITICAL,
        is_resolved=True,
    )

    # Catalog API
    catalog_url = reverse("intelligent_tracker_api:security-events-catalog-list")
    resp_cat = client.get(catalog_url)
    assert resp_cat.status_code == 200
    cat_data = resp_cat.json()
    results = cat_data["results"] if "results" in cat_data else cat_data
    assert len(results) >= 2

    # Filtering by severity
    resp_filter = client.get(f"{catalog_url}?severity=CRITICAL")
    assert resp_filter.status_code == 200
    filter_data = resp_filter.json()
    filter_results = filter_data["results"] if "results" in filter_data else filter_data
    assert len(filter_results) == 1
    assert filter_results[0]["severity"] == "CRITICAL"

    # Stats API
    stats_url = reverse("intelligent_tracker_api:security_stats")
    resp_stats = client.get(stats_url)
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert stats["total_events"] >= 2
    assert stats["unresolved_events"] >= 1
    assert "IntrusionAlert" in stats["events_by_type"]


@pytest.mark.django_db
def test_dashboard_and_detail_views(client, auth_user, test_location):
    # Unauthenticated redirect
    dashboard_url = reverse("intelligent_tracker_hub:dashboard")
    resp = client.get(dashboard_url)
    assert resp.status_code == 302

    # Authenticated dashboard
    client.force_login(auth_user)
    event = SecurityEvent.objects.create(
        event_type=SecurityEventType.INTRUSION,
        site=test_location,
        camera_id="cam-east-perimeter",
        severity=SecuritySeverity.HIGH,
        metadata={"zone_name": "Fence Line East"},
    )

    resp_auth = client.get(dashboard_url)
    assert resp_auth.status_code == 200
    content = resp_auth.content.decode("utf-8")
    assert "Edge AI Spatial Security Hub" in content
    assert "cam-east-perimeter" in content
    assert "Fence Line East" in content

    # Event Detail View
    detail_url = reverse("intelligent_tracker_hub:event_detail", kwargs={"event_id": event.event_id})
    resp_detail = client.get(detail_url)
    assert resp_detail.status_code == 200
    assert "Evidence Snapshot" in resp_detail.content.decode("utf-8")

    # Resolve action
    resolve_url = reverse("intelligent_tracker_hub:event_resolve", kwargs={"event_id": event.event_id})
    resp_res = client.post(resolve_url, {"resolution_notes": "Operator resolved false positive."})
    assert resp_res.status_code == 302
    event.refresh_from_db()
    assert event.is_resolved is True
    assert event.resolved_by == auth_user

    # Mock dispatch simulation
    sim_url = reverse("intelligent_tracker_hub:simulate_dispatch")
    resp_sim = client.post(sim_url, {
        "event_type": "FallDetectedAlert",
        "camera_id": "cam-sim-01",
        "zone_name": "Loading Dock",
        "site_id": test_location.id,
    })
    assert resp_sim.status_code == 302
    assert SecurityEvent.objects.filter(camera_id="cam-sim-01").exists()

    # Webhook Audit View
    audit_url = reverse("intelligent_tracker_hub:audit_log")
    resp_audit = client.get(audit_url)
    assert resp_audit.status_code == 200
    assert "Edge AI Webhook Audit Trail" in resp_audit.content.decode("utf-8")


def test_intelligent_tracker_plugin_discovery():
    plugin = registry.get_plugin("intelligent_tracker_hub")
    assert plugin is not None
    assert plugin.name == "intelligent_tracker_hub"
    assert plugin.icon == "fa fa-shield"
    assert len(plugin.menu_items) == 1
    assert plugin.menu_items[0].url_name == "intelligent_tracker_hub:dashboard"

