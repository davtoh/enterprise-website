import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import SecurityEvent, SecurityAuditLog, SecuritySeverity, Camera


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = (
        "short_uuid",
        "event_type",
        "severity_badge",
        "site",
        "camera_id",
        "timestamp",
        "is_resolved",
        "snapshot_thumb",
    )
    list_filter = ("event_type", "severity", "is_resolved", "site", "timestamp")
    search_fields = ("event_id", "camera_id", "resolution_notes", "metadata")
    readonly_fields = ("event_id", "created_at", "updated_at", "snapshot_thumb_large", "metadata_pretty")
    fieldsets = (
        (
            _("Event Information"),
            {
                "fields": (
                    "event_id",
                    "event_type",
                    "severity",
                    "site",
                    "camera_id",
                    "timestamp",
                )
            },
        ),
        (
            _("Evidence & Telemetry"),
            {
                "fields": (
                    "video_evidence",
                    "snapshot",
                    "snapshot_thumb_large",
                    "metadata_pretty",
                )
            },
        ),
        (
            _("Resolution & Incident Handling"),
            {
                "fields": (
                    "is_resolved",
                    "resolved_by",
                    "resolved_at",
                    "resolution_notes",
                )
            },
        ),
        (
            _("Audit Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def short_uuid(self, obj):
        return str(obj.event_id)[:8] + "..."
    short_uuid.short_description = _("Event ID")

    def severity_badge(self, obj):
        colors = {
            SecuritySeverity.CRITICAL: "#dc3545",
            SecuritySeverity.HIGH: "#fd7e14",
            SecuritySeverity.MEDIUM: "#0dcaf0",
            SecuritySeverity.LOW: "#6c757d",
        }
        color = colors.get(obj.severity, "#0d6efd")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.severity,
        )
    severity_badge.short_description = _("Severity")

    def snapshot_thumb(self, obj):
        if obj.snapshot:
            return format_html(
                '<img src="{}" style="width: 48px; height: 32px; object-fit: cover; border-radius: 4px;" />',
                obj.snapshot.url,
            )
        return "-"
    snapshot_thumb.short_description = _("Snapshot")

    def snapshot_thumb_large(self, obj):
        if obj.snapshot:
            return format_html(
                '<img src="{}" style="max-width: 400px; height: auto; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.2);" />',
                obj.snapshot.url,
            )
        return _("No snapshot uploaded.")
    snapshot_thumb_large.short_description = _("Snapshot Preview")

    def metadata_pretty(self, obj):
        return format_html(
            "<pre style='background: #f8f9fa; padding: 10px; border-radius: 4px;'>{}</pre>",
            json.dumps(obj.metadata, indent=2),
        )
    metadata_pretty.short_description = _("Formatted Metadata")


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "received_at",
        "ip_address",
        "endpoint",
        "http_method",
        "signature_valid_badge",
        "status_code",
        "processed_successfully",
    )
    list_filter = ("signature_valid", "processed_successfully", "status_code", "http_method")
    search_fields = ("event_id", "ip_address", "raw_payload", "error_message")
    readonly_fields = (
        "received_at",
        "ip_address",
        "endpoint",
        "http_method",
        "signature_header",
        "signature_valid",
        "event_id",
        "status_code",
        "error_message",
        "processed_successfully",
        "raw_payload",
    )

    def signature_valid_badge(self, obj):
        if obj.signature_valid:
            return format_html('<span style="color: green; font-weight: bold;">&#10004; VALID</span>')
        return format_html('<span style="color: red; font-weight: bold;">&#10008; INVALID</span>')
    signature_valid_badge.short_description = _("HMAC Status")


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "camera_id",
        "site",
        "status_badge",
        "fps",
        "resolution",
        "last_heartbeat",
        "is_active",
    )
    list_filter = ("status", "site", "is_active")
    search_fields = ("camera_id", "name", "stream_url")
    readonly_fields = ("created_at", "updated_at", "last_heartbeat")

    def status_badge(self, obj):
        colors = {
            "ONLINE": "#198754",
            "OFFLINE": "#6c757d",
            "CONNECTING": "#ffc107",
            "DEGRADED": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        text_color = "black" if obj.status == "CONNECTING" else "white"
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            text_color,
            obj.get_status_display(),
        )
    status_badge.short_description = _("Status")
