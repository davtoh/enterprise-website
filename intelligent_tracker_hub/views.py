import json
import uuid
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext as _
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .models import SecurityEvent, SecurityEventType, SecuritySeverity, SecurityAuditLog
from .security import calculate_hmac_signature, get_tracker_secret_key
from location_management.models import Location


class SecurityDashboardView(LoginRequiredMixin, TemplateView):
    """
    Central Security Operations Center (SOC) dashboard.
    Visualizes edge AI spatial security events, active cameras, and telemetry metrics.
    """

    template_name = "intelligent_tracker_hub/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        events_qs = SecurityEvent.objects.select_related("site", "resolved_by").all()

        # Filtering parameters
        event_type = self.request.GET.get("event_type")
        severity = self.request.GET.get("severity")
        status_filter = self.request.GET.get("status")
        camera_id = self.request.GET.get("camera_id")

        if event_type:
            events_qs = events_qs.filter(event_type=event_type)
        if severity:
            events_qs = events_qs.filter(severity=severity)
        if status_filter == "unresolved":
            events_qs = events_qs.filter(is_resolved=False)
        elif status_filter == "resolved":
            events_qs = events_qs.filter(is_resolved=True)
        if camera_id:
            events_qs = events_qs.filter(camera_id__icontains=camera_id)

        # Pagination
        paginator = Paginator(events_qs, 15)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # KPI Metrics
        total_events = SecurityEvent.objects.count()
        unresolved_count = SecurityEvent.objects.filter(is_resolved=False).count()
        critical_count = SecurityEvent.objects.filter(severity=SecuritySeverity.CRITICAL, is_resolved=False).count()
        high_count = SecurityEvent.objects.filter(severity=SecuritySeverity.HIGH, is_resolved=False).count()
        active_cameras = (
            SecurityEvent.objects.values("camera_id").distinct().count()
        )

        ctx.update(
            {
                "page_obj": page_obj,
                "events": page_obj.object_list,
                "total_events": total_events,
                "unresolved_count": unresolved_count,
                "critical_count": critical_count,
                "high_count": high_count,
                "active_cameras": active_cameras,
                "event_types": SecurityEventType.choices,
                "severities": SecuritySeverity.choices,
                "selected_event_type": event_type or "",
                "selected_severity": severity or "",
                "selected_status": status_filter or "",
                "selected_camera_id": camera_id or "",
                "locations": Location.objects.filter(is_active=True),
            }
        )
        return ctx


class SecurityEventDetailView(LoginRequiredMixin, DetailView):
    """
    Detailed inspection view for an individual spatial security event with evidence snapshot and telemetry metadata.
    """

    model = SecurityEvent
    template_name = "intelligent_tracker_hub/event_detail.html"
    context_object_name = "event"
    slug_field = "event_id"
    slug_url_kwarg = "event_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["metadata_formatted"] = json.dumps(self.object.metadata, indent=2)
        return ctx


class SecurityEventResolveView(LoginRequiredMixin, View):
    """
    Operator action to acknowledge and resolve a security event.
    """

    def post(self, request, event_id):
        event = get_object_or_404(SecurityEvent, event_id=event_id)
        notes = request.POST.get("resolution_notes", "").strip()
        event.resolve(request.user, notes=notes)
        messages.success(request, _("Security event %s marked as resolved.") % event.event_id)
        return redirect("intelligent_tracker_hub:event_detail", event_id=event.event_id)


class SecurityAuditLogListView(LoginRequiredMixin, ListView):
    """
    Audit trail view of webhook requests and HMAC signature validation logs.
    """

    model = SecurityAuditLog
    template_name = "intelligent_tracker_hub/audit_log.html"
    context_object_name = "logs"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        valid = self.request.GET.get("valid")
        if valid == "true":
            qs = qs.filter(signature_valid=True)
        elif valid == "false":
            qs = qs.filter(signature_valid=False)
        return qs


class SecurityMockDispatchView(LoginRequiredMixin, View):
    """
    Developer/Operator helper tool to simulate an edge AI vision alert payload locally with HMAC signing.
    """

    def post(self, request):
        event_type = request.POST.get("event_type", SecurityEventType.INTRUSION)
        camera_id = request.POST.get("camera_id", "cam-north-gate-01")
        zone_name = request.POST.get("zone_name", "Perimeter Zone A")
        site_id = request.POST.get("site_id")

        site_obj = None
        if site_id:
            site_obj = Location.objects.filter(id=site_id).first()

        event = SecurityEvent.objects.create(
            event_id=uuid.uuid4(),
            event_type=event_type,
            camera_id=camera_id,
            site=site_obj,
            timestamp=timezone.now(),
            metadata={
                "zone_name": zone_name,
                "confidence": 0.95,
                "dwell_seconds": 12.4,
                "simulated": True,
            },
            severity=(
                SecuritySeverity.CRITICAL
                if event_type == SecurityEventType.FALL_DETECTED
                else SecuritySeverity.HIGH
            ),
        )

        # Log simulated audit entry
        SecurityAuditLog.objects.create(
            ip_address="127.0.0.1",
            endpoint="/security/simulate/",
            http_method="POST",
            signature_header="simulated-local-dispatch",
            signature_valid=True,
            event_id=str(event.event_id),
            status_code=201,
            raw_payload=f"Simulated local dispatch: {event.event_type} on {camera_id}",
            processed_successfully=True,
        )

        messages.success(request, _("Simulated security event %s created successfully.") % event.event_id)
        return redirect("intelligent_tracker_hub:dashboard")
