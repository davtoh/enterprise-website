"""
Test Suite Facade: Intelligent Tracker Hub Subsystem.

Backward-compatible re-export module routing tests to focused domain test modules in `tests/tracker/`:
- `test_security_events`: HMAC verification, webhook receiver, catalog, stats, and dashboard views.
- `test_video_evidence`: Zero-copy registration, range-request stream proxy, cloud archival, and self-healing.
- `test_cameras`: Model properties, heartbeats, viewsets, synthetic MJPEG, proxy, and telemetry.
- `test_access_control`: Physical gate access, ETag whitelist delta-sync, and visitor notifications.
"""

from .tracker.conftest import (
    SAMPLE_PNG_BASE64,
    auth_user,
    test_location,
    test_company,
    test_contacts,
)

from .tracker.test_security_events import (
    test_calculate_and_verify_hmac_signature,
    test_webhook_missing_hmac_returns_401,
    test_webhook_invalid_hmac_returns_401,
    test_webhook_valid_hmac_success,
    test_webhook_with_base64_snapshot_and_site_code,
    test_webhook_invalid_payload_returns_400,
    test_security_event_model,
    test_security_audit_log_model,
    test_security_catalog_and_stats_api,
    test_dashboard_and_detail_views,
    test_intelligent_tracker_plugin_discovery,
)

from .tracker.test_video_evidence import (
    test_video_evidence_zero_copy_register,
    test_video_evidence_register_tampered_hmac,
    test_video_evidence_stream_gateway_remote_proxy,
    test_video_evidence_stream_gateway_local_archived,
    test_video_evidence_archive_action,
    test_video_evidence_upload_multipart,
    test_event_detail_view_renders_video_evidence,
    test_video_evidence_corruption_auto_fallback_to_reference,
    test_video_evidence_forced_repair_from_reference,
)

from .tracker.test_cameras import (
    test_camera_model_creation_and_properties,
    test_camera_heartbeat_api_unauthorized,
    test_camera_heartbeat_api_hmac_success,
    test_camera_viewset_list_and_filter,
    test_live_stream_proxy_synthetic_stream,
    test_live_stream_proxy_fallback_on_unreachable_edge,
    test_live_telemetry_stream_api,
    test_soc_dashboard_view_camera_grid,
)

from .tracker.test_access_control import (
    test_crm_contact_physical_security_credentials_and_methods,
    test_visitor_access_log_model,
    test_whitelist_delta_sync_api_unauthorized,
    test_whitelist_delta_sync_api_success_and_etag,
    test_whitelist_delta_sync_api_filters_expired_passes_and_marks_banned,
    test_whitelist_delta_sync_api_since_parameter,
    test_security_access_ingest_api_unauthorized,
    test_security_access_ingest_entry_granted_and_presence_update,
    test_security_access_ingest_exit_and_presence_update,
    test_security_access_ingest_by_license_plate_anpr,
    test_security_access_ingest_banned_contact_escalates_to_security_event,
    test_visitor_arrival_notification_service,
    test_visitor_access_catalog_viewset,
)
