import uuid
from rest_framework import serializers
from .models import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityAuditLog,
    Camera,
    CameraStatus,
    VisitorAccessLog,
)

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


class CRMContactWhitelistItemSerializer(serializers.Serializer):
    """
    Serializes an authoritative CRM contact record for edge whitelist synchronization.
    """

    contact_id = serializers.IntegerField(source="id")
    full_name = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_blank=True)
    company_name = serializers.CharField(source="company.name", default="", allow_null=True)
    security_clearance = serializers.CharField()
    security_tag = serializers.CharField(allow_blank=True)
    license_plate = serializers.CharField(allow_blank=True)
    normalized_license_plate = serializers.CharField()
    valid_from = serializers.DateTimeField(allow_null=True)
    valid_until = serializers.DateTimeField(allow_null=True)
    is_pass_valid = serializers.BooleanField()
    is_banned = serializers.SerializerMethodField()
    presence_status = serializers.CharField()
    face_profile_photo_url = serializers.SerializerMethodField()
    face_embedding_vector = serializers.ListField(child=serializers.FloatField(), default=list)
    updated_at = serializers.DateTimeField()

    def get_is_banned(self, obj) -> bool:
        return obj.security_clearance == "BANNED"

    def get_face_profile_photo_url(self, obj) -> str:
        if obj.face_profile_photo:
            try:
                return obj.face_profile_photo.url
            except Exception:
                pass
        return ""


class SecurityAccessIngestSerializer(serializers.Serializer):
    """
    Validates physical gate access events ingested from edge AI vision nodes.
    Supports recognition via contact ID, vehicle license plate, or security RFID/tag.
    """

    site_id = serializers.IntegerField(required=False, allow_null=True)
    site_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    camera_id = serializers.CharField(max_length=100)
    contact_id = serializers.IntegerField(required=False, allow_null=True)
    license_plate = serializers.CharField(max_length=30, required=False, allow_blank=True)
    security_tag = serializers.CharField(max_length=100, required=False, allow_blank=True)
    direction = serializers.ChoiceField(choices=["ENTRY", "EXIT"], default="ENTRY")
    verification_method = serializers.ChoiceField(
        choices=["face", "plate", "tag", "manual"],
        default="face",
    )
    confidence = serializers.FloatField(required=False, allow_null=True)
    access_granted = serializers.BooleanField(required=False, default=True)
    denial_reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    timestamp = serializers.DateTimeField(required=False)
    snapshot_base64 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    metadata = serializers.DictField(required=False, default=dict)


class VisitorAccessLogSerializer(serializers.ModelSerializer):
    """
    Detailed read representation of VisitorAccessLog records.
    """

    contact_name = serializers.CharField(source="contact.full_name", default="", read_only=True)
    contact_clearance = serializers.CharField(source="contact.security_clearance", default="", read_only=True)
    site_name = serializers.CharField(source="site.name", default="", read_only=True)
    status_badge_class = serializers.CharField(read_only=True)
    snapshot_url = serializers.SerializerMethodField()

    class Meta:
        model = VisitorAccessLog
        fields = [
            "id",
            "access_id",
            "contact",
            "contact_name",
            "contact_clearance",
            "site",
            "site_name",
            "camera_id",
            "direction",
            "verification_method",
            "recognized_identifier",
            "confidence",
            "access_granted",
            "denial_reason",
            "status_badge_class",
            "timestamp",
            "snapshot",
            "snapshot_url",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "access_id", "created_at"]

    def get_snapshot_url(self, obj) -> str:
        if obj.snapshot:
            try:
                return obj.snapshot.url
            except Exception:
                pass
        return ""


