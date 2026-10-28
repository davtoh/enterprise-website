from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    SecurityEventWebhookApiView,
    SecurityEventViewSet,
    SecurityAuditLogViewSet,
    SecurityStatsApiView,
    VideoEvidenceRegisterApiView,
    VideoEvidenceUploadApiView,
    VideoEvidenceStreamGatewayApiView,
    VideoEvidenceArchiveApiView,
    CameraViewSet,
    CameraHeartbeatApiView,
    LiveStreamProxyApiView,
    LiveTelemetryStreamApiView,
    WhitelistDeltaSyncApiView,
    SecurityAccessIngestApiView,
    VisitorAccessLogViewSet,
)

app_name = "intelligent_tracker_api"

router = DefaultRouter()
router.register(r"events/catalog", SecurityEventViewSet, basename="security-events-catalog")
router.register(r"audit", SecurityAuditLogViewSet, basename="security-audit-logs")
router.register(r"cameras", CameraViewSet, basename="cameras")
router.register(r"access/catalog", VisitorAccessLogViewSet, basename="visitor-access-catalog")

urlpatterns = [
    # Primary edge webhook receiver specified in INTELLIGENT_TRACKER_INTEGRATION_PLAN.md
    path("security/events/", SecurityEventWebhookApiView.as_view(), name="security_event_webhook"),
    path("security/stats/", SecurityStatsApiView.as_view(), name="security_stats"),
    path("security/cameras/heartbeat/", CameraHeartbeatApiView.as_view(), name="camera_heartbeat"),
    path("security/stream/live/<str:camera_id>/", LiveStreamProxyApiView.as_view(), name="camera_stream_live"),
    path("security/stream/telemetry/<str:camera_id>/", LiveTelemetryStreamApiView.as_view(), name="camera_telemetry_live"),

    # CRM Visitor Passes & Bi-directional Access Loop (Phase E4 - Frontier SOTA)
    path("security/whitelist/", WhitelistDeltaSyncApiView.as_view(), name="security_whitelist"),
    path("security/access/", SecurityAccessIngestApiView.as_view(), name="security_access"),

    path("security/", include(router.urls)),

    # Video Evidence Ingestion & Zero-Copy Stream Gateway (Milestone 16b / Phase E2)
    path("gallery/register/", VideoEvidenceRegisterApiView.as_view(), name="video_gallery_register"),
    path("gallery/upload/", VideoEvidenceUploadApiView.as_view(), name="video_gallery_upload"),
    path("gallery/stream/<int:video_id>/", VideoEvidenceStreamGatewayApiView.as_view(), name="video_gallery_stream"),
    path("gallery/archive/<int:video_id>/", VideoEvidenceArchiveApiView.as_view(), name="video_gallery_archive"),
]


