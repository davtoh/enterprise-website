import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SecurityEventType(models.TextChoices):
    INTRUSION = "IntrusionAlert", _("Intrusion Alert")
    RESTRICTED_ENTITY = "RestrictedEntityAlert", _("Restricted Entity Alert")
    OCCUPANCY_THRESHOLD = "OccupancyThresholdEvent", _("Occupancy Threshold Event")
    FALL_DETECTED = "FallDetectedAlert", _("Fall Detected Alert")
    LOITERING = "LoiteringAlert", _("Loitering Alert")
    LINE_CROSS = "LineCrossAlert", _("Line Cross Alert")


class SecuritySeverity(models.TextChoices):
    LOW = "LOW", _("Low")
    MEDIUM = "MEDIUM", _("Medium")
    HIGH = "HIGH", _("High")
    CRITICAL = "CRITICAL", _("Critical")


class CameraStatus(models.TextChoices):
    ONLINE = "ONLINE", _("Online")
    OFFLINE = "OFFLINE", _("Offline")
    CONNECTING = "CONNECTING", _("Connecting")
    DEGRADED = "DEGRADED", _("Degraded")


class Camera(models.Model):
    """
    Edge AI Camera Node connected to the Enterprise Security Hub.
    Represents an IP camera / RTSP stream processed by intelligent-tracker.
    """

    camera_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Camera Identifier"),
        help_text=_("Unique identifier (e.g. cam-north-gate-01)"),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Camera Name"),
        help_text=_("Human-readable label (e.g. North Perimeter Fence)"),
    )
    site = models.ForeignKey(
        "location_management.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cameras",
        verbose_name=_("Site / Facility"),
    )
    stream_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name=_("Edge Stream URL"),
        help_text=_("Edge MJPEG stream URL (e.g. http://edge-node:8000/live/cam-01/ or mock://)"),
    )
    status = models.CharField(
        max_length=20,
        choices=CameraStatus.choices,
        default=CameraStatus.OFFLINE,
        db_index=True,
        verbose_name=_("Connection Status"),
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Last Heartbeat"),
    )
    fps = models.IntegerField(
        default=30,
        verbose_name=_("Target FPS"),
    )
    resolution = models.CharField(
        max_length=50,
        default="1920x1080",
        verbose_name=_("Stream Resolution"),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Camera Telemetry Metadata"),
        help_text=_("Dropped frames, bitrate, inference model, active trackers"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Updated"))

    class Meta:
        verbose_name = _("Camera")
        verbose_name_plural = _("Cameras")
        ordering = ["site", "name"]

    def __str__(self):
        return f"{self.name} ({self.camera_id})"

    @property
    def is_alive(self) -> bool:
        """Returns True if a heartbeat was received within the last 90 seconds and status is ONLINE."""
        if not self.last_heartbeat or self.status != CameraStatus.ONLINE:
            return False
        return (timezone.now() - self.last_heartbeat).total_seconds() < 90

    @property
    def status_badge_class(self) -> str:
        mapping = {
            CameraStatus.ONLINE: "success",
            CameraStatus.OFFLINE: "secondary",
            CameraStatus.CONNECTING: "warning text-dark",
            CameraStatus.DEGRADED: "danger",
        }
        return mapping.get(self.status, "secondary")

    def get_stream_proxy_url(self) -> str:
        return reverse("intelligent_tracker_api:camera_stream_live", kwargs={"camera_id": self.camera_id})

    def get_telemetry_url(self) -> str:
        return reverse("intelligent_tracker_api:camera_telemetry_live", kwargs={"camera_id": self.camera_id})


class SecurityEvent(models.Model):
    """
    Spatial security event ingested from Edge AI vision nodes (intelligent-tracker).
    """

    event_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_("Event UUID"),
    )
    event_type = models.CharField(
        max_length=50,
        choices=SecurityEventType.choices,
        default=SecurityEventType.INTRUSION,
        db_index=True,
        verbose_name=_("Event Type"),
    )
    site = models.ForeignKey(
        "location_management.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_events",
        verbose_name=_("Site / Facility"),
    )
    camera_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Camera Identifier"),
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_("Event Timestamp"),
    )
    snapshot = models.ImageField(
        upload_to="security_events/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Evidence Snapshot"),
    )
    video_evidence = models.ForeignKey(
        "video_gallery.VideoItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_events",
        verbose_name=_("Video Evidence"),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Telemetry & Dwell Metadata"),
    )
    severity = models.CharField(
        max_length=20,
        choices=SecuritySeverity.choices,
        default=SecuritySeverity.HIGH,
        db_index=True,
        verbose_name=_("Severity Level"),
    )
    is_resolved = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Resolved"),
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_security_events",
        verbose_name=_("Resolved By"),
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Resolved At"),
    )
    resolution_notes = models.TextField(
        blank=True,
        verbose_name=_("Resolution Notes"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ingested At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Updated"))

    class Meta:
        verbose_name = _("Security Event")
        verbose_name_plural = _("Security Events")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["is_resolved", "severity"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.get_event_type_display()} - {self.camera_id} ({self.event_id})"

    def get_absolute_url(self):
        return reverse("intelligent_tracker_hub:event_detail", kwargs={"event_id": self.event_id})

    def resolve(self, user, notes: str = ""):
        """Mark event as resolved by an authorized operator."""
        self.is_resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=["is_resolved", "resolved_by", "resolved_at", "resolution_notes", "updated_at"])

    @property
    def zone_name(self) -> str:
        return self.metadata.get("zone_name", "")

    @property
    def dwell_seconds(self):
        return self.metadata.get("dwell_seconds")

    @property
    def confidence(self):
        return self.metadata.get("confidence")

    @property
    def entity_id(self) -> str:
        return str(self.metadata.get("entity_id", ""))

    @property
    def camera_obj(self):
        """Resolves associated Camera entity if provisioned."""
        return Camera.objects.filter(camera_id=self.camera_id).first()

    @property
    def severity_badge_class(self) -> str:
        mapping = {
            SecuritySeverity.CRITICAL: "danger",
            SecuritySeverity.HIGH: "warning text-dark",
            SecuritySeverity.MEDIUM: "info text-dark",
            SecuritySeverity.LOW: "secondary",
        }
        return mapping.get(self.severity, "primary")


class SecurityAuditLog(models.Model):
    """
    Immutable audit log of all edge webhook incoming requests, HMAC authentication verdicts, and error payloads.
    """

    received_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Received At"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("Client IP"))
    endpoint = models.CharField(max_length=255, default="/api/v1/security/events/", verbose_name=_("Endpoint"))
    http_method = models.CharField(max_length=10, default="POST", verbose_name=_("HTTP Method"))
    signature_header = models.CharField(max_length=255, blank=True, verbose_name=_("X-Tracker-Signature Header"))
    signature_valid = models.BooleanField(default=False, db_index=True, verbose_name=_("Signature Valid"))
    event_id = models.CharField(max_length=100, blank=True, db_index=True, verbose_name=_("Associated Event UUID"))
    raw_payload = models.TextField(blank=True, verbose_name=_("Raw Request Body"))
    status_code = models.IntegerField(default=200, verbose_name=_("HTTP Status Code"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Details"))
    processed_successfully = models.BooleanField(default=False, db_index=True, verbose_name=_("Processed Successfully"))

    class Meta:
        verbose_name = _("Security Audit Log")
        verbose_name_plural = _("Security Audit Logs")
        ordering = ["-received_at"]

    def __str__(self):
        status = "OK" if self.processed_successfully else "FAILED"
        return f"{self.received_at:%Y-%m-%d %H:%M:%S} - {self.http_method} {self.endpoint} [{self.status_code}] ({status})"


class AccessDirection(models.TextChoices):
    ENTRY = "ENTRY", _("Entry")
    EXIT = "EXIT", _("Exit")


class VerificationMethod(models.TextChoices):
    FACE = "face", _("Facial Recognition")
    PLATE = "plate", _("License Plate (ANPR)")
    TAG = "tag", _("Security Tag / RFID")
    MANUAL = "manual", _("Manual Operator Override")


class VisitorAccessLog(models.Model):
    """
    Physical security access log tracking gate entry and exit events processed by intelligent-tracker.
    Provides bi-directional integration with CRM Contact presence and security clearances.
    """

    access_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_("Access UUID"),
    )
    contact = models.ForeignKey(
        "crm.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
        verbose_name=_("CRM Contact"),
    )
    site = models.ForeignKey(
        "location_management.Location",
        on_delete=models.CASCADE,
        related_name="access_logs",
        verbose_name=_("Facility / Site"),
    )
    camera_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Gate Camera ID"),
        help_text=_("Identifier of camera covering the access point (e.g. cam-north-gate-entry)"),
    )
    direction = models.CharField(
        max_length=10,
        choices=AccessDirection.choices,
        default=AccessDirection.ENTRY,
        db_index=True,
        verbose_name=_("Access Direction"),
    )
    verification_method = models.CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        default=VerificationMethod.FACE,
        db_index=True,
        verbose_name=_("Verification Method"),
    )
    recognized_identifier = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Recognized Identifier"),
        help_text=_("Plate string, face track ID, or RFID code matched at the edge"),
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("Detection Confidence"),
    )
    access_granted = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Access Granted"),
    )
    denial_reason = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Denial Reason"),
        help_text=_("Reason for access denial (e.g. Pass Expired, Banned Entity, Unrecognized)"),
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_("Event Timestamp"),
    )
    snapshot = models.ImageField(
        upload_to="security_access/%Y/%m/%d/",
        blank=True,
        null=True,
        verbose_name=_("Access Snapshot"),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Access Telemetry Metadata"),
        help_text=_("Gate turnstile number, ambient temperature, vehicle make/model"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ingested At"))

    class Meta:
        verbose_name = _("Visitor Access Log")
        verbose_name_plural = _("Visitor Access Logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["site", "timestamp"]),
            models.Index(fields=["access_granted", "direction"]),
        ]

    def __str__(self):
        status = "GRANTED" if self.access_granted else f"DENIED ({self.denial_reason})"
        person = self.contact.full_name if self.contact else (self.recognized_identifier or "Unknown")
        return f"[{self.direction}] {person} @ {self.camera_id} - {status}"

    @property
    def status_badge_class(self) -> str:
        return "success" if self.access_granted else "danger"

