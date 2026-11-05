"""
Intelligent Tracker Hub API Package.
Provides cohesive submodules for edge AI vision node webhooks, video evidence,
live streaming gateways, camera telemetry, and CRM access control.
"""

from .security_events import (
    SecurityEventWebhookApiView,
    SecurityEventViewSet,
    SecurityAuditLogViewSet,
    SecurityStatsApiView,
)
from .video_evidence import (
    VideoEvidenceRegisterApiView,
    VideoEvidenceUploadApiView,
)
from .video_streaming import (
    VideoEvidenceStreamGatewayApiView,
    VideoEvidenceArchiveApiView,
)
from .streaming import (
    generate_synthetic_mjpeg_stream,
    stream_mjpeg_gateway,
    LiveStreamProxyApiView,
    LiveTelemetryStreamApiView,
)
from .cameras import (
    CameraHeartbeatApiView,
    CameraViewSet,
)
from .whitelist_sync import (
    WhitelistDeltaSyncApiView,
)
from .access_control import (
    SecurityAccessIngestApiView,
    VisitorAccessLogViewSet,
)

__all__ = [
    "SecurityEventWebhookApiView",
    "SecurityEventViewSet",
    "SecurityAuditLogViewSet",
    "SecurityStatsApiView",
    "VideoEvidenceRegisterApiView",
    "VideoEvidenceUploadApiView",
    "VideoEvidenceStreamGatewayApiView",
    "VideoEvidenceArchiveApiView",
    "generate_synthetic_mjpeg_stream",
    "stream_mjpeg_gateway",
    "LiveStreamProxyApiView",
    "LiveTelemetryStreamApiView",
    "CameraHeartbeatApiView",
    "CameraViewSet",
    "WhitelistDeltaSyncApiView",
    "SecurityAccessIngestApiView",
    "VisitorAccessLogViewSet",
]
