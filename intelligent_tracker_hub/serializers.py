import uuid
from rest_framework import serializers
from .models import SecurityEvent, SecurityEventType, SecuritySeverity, SecurityAuditLog, Camera, CameraStatus
from location_management.models import Location


class SecurityEventWebhookSerializer(serializers.Serializer):
    """
    Validates incoming edge AI vision webhook payloads from davtoh/intelligent-tracker.
    """

    event_id = serializers.UUIDField(required=False, default=uuid.uuid4)
    event_type = serializers.ChoiceField(choices=SecurityEventType.choices)
    site_id = serializers.IntegerField(required=False, allow_null=True)
    site_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    camera_id = serializers.CharField(max_length=100)
    timestamp = serializers.DateTimeField(required=False)
    snapshot_base64 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)
    severity = serializers.ChoiceField(choices=SecuritySeverity.choices, required=False, allow_blank=True)


class LocationSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name", "code", "address"]


class SecurityEventSerializer(serializers.ModelSerializer):
    """
    Read/write representation of SecurityEvent records.
    """

    site_details = LocationSimpleSerializer(source="site", read_only=True)
    resolved_by_username = serializers.CharField(source="resolved_by.username", read_only=True, default="")
    snapshot_url = serializers.SerializerMethodField()
    video_stream_url = serializers.SerializerMethodField()
    video_title = serializers.CharField(source="video_evidence.title", read_only=True, default="")

    class Meta:
        model = SecurityEvent
        fields = [
            "id",
            "event_id",
            "event_type",
            "site",
            "site_details",
            "camera_id",
            "timestamp",
            "snapshot",
            "snapshot_url",
            "video_evidence",
            "video_stream_url",
            "video_title",
            "metadata",
            "severity",
            "is_resolved",
            "resolved_by",
            "resolved_by_username",
            "resolved_at",
            "resolution_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "event_id", "created_at", "updated_at"]

    def get_snapshot_url(self, obj) -> str:
        if obj.snapshot:
            try:
                return obj.snapshot.url
            except Exception:
                pass
        return ""

    def get_video_stream_url(self, obj) -> str:
        if obj.video_evidence_id:
            return f"/api/v1/gallery/stream/{obj.video_evidence_id}/"
        return ""


class VideoEvidenceRegisterSerializer(serializers.Serializer):
    """
    Validates zero-copy lightweight video evidence registration payloads from edge nodes.
    Stores remote stream URLs without uploading heavy MP4 bytes.
    """

    event_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(max_length=255)
    source_url = serializers.URLField(max_length=500)
    site_id = serializers.IntegerField(required=False, allow_null=True)
    site_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    site_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    camera_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    duration_seconds = serializers.FloatField(required=False, allow_null=True)
    thumbnail_base64 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    trajectory = serializers.ListField(required=False, default=list)
    metadata = serializers.DictField(required=False, default=dict)


class VideoEvidenceUploadSerializer(serializers.Serializer):
    """
    Validates traditional multipart/form-data MP4 uploads for isolated edge nodes.
    """

    file = serializers.FileField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    event_id = serializers.UUIDField(required=False, allow_null=True)
    site_id = serializers.IntegerField(required=False, allow_null=True)
    site_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    site_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    camera_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    thumbnail_base64 = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SecurityAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityAuditLog
        fields = "__all__"


class CameraSerializer(serializers.ModelSerializer):
    """
    Representation of connected Camera endpoints, connection status, and stream URLs.
    """

    site_details = LocationSimpleSerializer(source="site", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_alive = serializers.BooleanField(read_only=True)
    status_badge_class = serializers.CharField(read_only=True)
    stream_proxy_url = serializers.CharField(source="get_stream_proxy_url", read_only=True)
    telemetry_url = serializers.CharField(source="get_telemetry_url", read_only=True)

    class Meta:
        model = Camera
        fields = [
            "id",
            "camera_id",
            "name",
            "site",
            "site_details",
            "stream_url",
            "status",
            "status_display",
            "status_badge_class",
            "is_alive",
            "last_heartbeat",
            "fps",
            "resolution",
            "is_active",
            "metadata",
            "stream_proxy_url",
            "telemetry_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CameraHeartbeatSerializer(serializers.Serializer):
    """
    Validates periodic health heartbeats emitted by edge inference nodes.
    """

    camera_id = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=CameraStatus.choices, required=False, default=CameraStatus.ONLINE)
    fps = serializers.IntegerField(required=False, default=30)
    resolution = serializers.CharField(max_length=50, required=False, default="1920x1080")
    stream_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    site_id = serializers.IntegerField(required=False, allow_null=True)
    site_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    metadata = serializers.DictField(required=False, default=dict)

