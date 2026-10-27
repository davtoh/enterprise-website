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
)

app_name = "intelligent_tracker_api"

router = DefaultRouter()
router.register(r"events/catalog", SecurityEventViewSet, basename="security-events-catalog")
router.register(r"audit", SecurityAuditLogViewSet, basename="security-audit-logs")

urlpatterns = [
    # Primary edge webhook receiver specified in INTELLIGENT_TRACKER_INTEGRATION_PLAN.md
    path("security/events/", SecurityEventWebhookApiView.as_view(), name="security_event_webhook"),
    path("security/stats/", SecurityStatsApiView.as_view(), name="security_stats"),
    path("security/", include(router.urls)),

    # Video Evidence Ingestion & Zero-Copy Stream Gateway (Milestone 16b / Phase E2)
    path("gallery/register/", VideoEvidenceRegisterApiView.as_view(), name="video_gallery_register"),
    path("gallery/upload/", VideoEvidenceUploadApiView.as_view(), name="video_gallery_upload"),
    path("gallery/stream/<int:video_id>/", VideoEvidenceStreamGatewayApiView.as_view(), name="video_gallery_stream"),
    path("gallery/archive/<int:video_id>/", VideoEvidenceArchiveApiView.as_view(), name="video_gallery_archive"),
]

