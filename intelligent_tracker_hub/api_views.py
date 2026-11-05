"""
Intelligent Tracker Hub API Views Facade.

Backward-compatible re-export module routing calls to focused domain submodules
in `intelligent_tracker_hub.api`:
- `security_events`: Webhook receiver, REST catalog, audit log, and incident statistics.
- `video_evidence`: Zero-copy edge registration and multipart MP4 uploads.
- `video_streaming`: Range-request stream gateway and self-healing cloud archival.
- `streaming`: Synthetic MJPEG stream generation, live reverse proxy, and telemetry streams.
- `cameras`: Edge heartbeat ingestion and camera catalog management.
- `whitelist_sync`: ETag-enabled contact delta-synchronization.
- `access_control`: Physical gate access decision engine and access logs catalog.
"""

import logging
import requests

from .api.security_events import (
    SecurityEventWebhookApiView,
    SecurityEventViewSet,
    SecurityAuditLogViewSet,
    SecurityStatsApiView,
)
from .api.video_evidence import (
    VideoEvidenceRegisterApiView,
    VideoEvidenceUploadApiView,
)
from .api.video_streaming import (
    VideoEvidenceStreamGatewayApiView,
    VideoEvidenceArchiveApiView,
)
from .api.streaming import (
    generate_synthetic_mjpeg_stream,
    stream_mjpeg_gateway,
    LiveStreamProxyApiView,
    LiveTelemetryStreamApiView,
)
from .api.cameras import (
    CameraHeartbeatApiView,
    CameraViewSet,
)
from .api.whitelist_sync import (
    WhitelistDeltaSyncApiView,
)
from .api.access_control import (
    SecurityAccessIngestApiView,
    VisitorAccessLogViewSet,
)

logger = logging.getLogger(__name__)

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
    "requests",
    "logger",
]
