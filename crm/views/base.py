import base64
import json
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.generic import TemplateView

from ..models import (
    Lead,
    LeadStage,
    InteractionLog,
    EmailSequence,
    EmailDeliveryLog,
    Segment,
)
from ..utils import get_crm_analytics_data


class CRMBaseView(LoginRequiredMixin):
    """Base mixin for CRM views enforcing authentication."""
    pass


# ==============================================================================
# Dashboard & Kanban Pipeline
# ==============================================================================

class DashboardView(CRMBaseView, TemplateView):
    template_name = "crm/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        analytics = get_crm_analytics_data()
        ctx["kpi"] = analytics["kpi"]

        # Stage distribution
        stage_data = []
        for stage in LeadStage:
            leads_in_stage = Lead.objects.filter(stage=stage.value)
            count = leads_in_stage.count()
            val = leads_in_stage.aggregate(s=Sum("value"))["s"] or Decimal("0.00")
            stage_data.append({
                "key": stage.value,
                "label": stage.label,
                "count": count,
                "value": val,
            })
        ctx["stage_data"] = stage_data

        # Recent records
        ctx["recent_leads"] = Lead.objects.select_related("contact", "company", "assigned_to")[:8]
        ctx["recent_interactions"] = InteractionLog.objects.select_related("lead", "contact", "user")[:8]
        ctx["active_sequences_count"] = EmailSequence.objects.filter(is_active=True).count()
        ctx["active_segments_count"] = Segment.objects.count()

        return ctx


class PipelineView(CRMBaseView, TemplateView):
    template_name = "crm/pipeline.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        stages = []
        for stage in LeadStage:
            leads = Lead.objects.filter(stage=stage.value).select_related(
                "contact", "company", "assigned_to"
            )
            total_val = leads.aggregate(s=Sum("value"))["s"] or Decimal("0.00")
            stages.append({
                "value": stage.value,
                "label": stage.label,
                "leads": leads,
                "count": leads.count(),
                "total_val": total_val,
            })
        ctx["stages"] = stages
        ctx["all_stages"] = LeadStage.choices
        return ctx


# ==============================================================================
# Analytics Dashboard Views
# ==============================================================================

class AnalyticsView(CRMBaseView, TemplateView):
    template_name = "crm/analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        data = get_crm_analytics_data()
        ctx["kpi"] = data["kpi"]
        ctx["analytics_json"] = json.dumps(data)
        return ctx


class AnalyticsDataApiView(CRMBaseView, View):
    """JSON API endpoint providing real-time data for Chart.js charts."""
    def get(self, request):
        data = get_crm_analytics_data()
        return JsonResponse(data)


# ==============================================================================
# Tracking Pixel View
# ==============================================================================

# 1x1 transparent GIF bytes
TRANSPARENT_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


class EmailTrackingPixelView(View):
    """
    Public 1x1 tracking pixel endpoint. Records email open events
    without disrupting email rendering.
    """
    def get(self, request, token):
        delivery_log = EmailDeliveryLog.objects.filter(tracking_token=token).first()
        if delivery_log:
            delivery_log.record_opened()

        response = HttpResponse(TRANSPARENT_GIF, content_type="image/gif")
        response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response

