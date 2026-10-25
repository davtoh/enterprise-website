import base64
import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .forms import (
    CompanyForm,
    ContactForm,
    LeadForm,
    InteractionLogForm,
    EmailSequenceForm,
    EmailStepForm,
    SegmentForm,
    BroadcastEmailForm,
)
from .models import (
    Company,
    Contact,
    Lead,
    LeadStage,
    InteractionLog,
    InteractionType,
    EmailSequence,
    EmailStep,
    SequenceEnrollment,
    SequenceEnrollmentStatus,
    EmailDeliveryLog,
    EmailDeliveryStatus,
    Segment,
)
from .tasks import process_email_sequences, send_segment_broadcast
from .utils import get_crm_analytics_data


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


class LeadStageUpdateView(CRMBaseView, View):
    """
    POST endpoint to update a lead's pipeline stage (called via HTMX, Alpine.js, or standard form).
    Automatically logs stage change in InteractionLog and checks sequence triggers.
    """
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        new_stage = request.POST.get("stage", "").strip().lower()
        note = request.POST.get("note", "").strip()

        if new_stage not in LeadStage.values:
            return JsonResponse({"error": _("Invalid stage specified.")}, status=400)

        changed = lead.change_stage(new_stage, user=request.user, note=note)

        if request.headers.get("HX-Request"):
            # Return partial card or status
            return render(request, "crm/partials/lead_kanban_card.html", {
                "lead": lead,
                "all_stages": LeadStage.choices,
            })

        if request.headers.get("Accept") == "application/json" or request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "changed": changed,
                "lead_id": lead.id,
                "new_stage": lead.stage,
                "stage_display": lead.get_stage_display(),
            })

        messages.success(request, _("Lead stage updated successfully to '%s'.") % lead.get_stage_display())
        return redirect(request.POST.get("next") or reverse("crm:pipeline"))


# ==============================================================================
# Lead Views
# ==============================================================================

class LeadListView(CRMBaseView, ListView):
    model = Lead
    template_name = "crm/lead_list.html"
    context_object_name = "leads"
    paginate_by = 20

    def get_queryset(self):
        qs = Lead.objects.select_related("contact", "company", "assigned_to")
        q = self.request.GET.get("q", "").strip()
        stage = self.request.GET.get("stage", "").strip()

        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(contact__first_name__icontains=q) |
                Q(contact__last_name__icontains=q) |
                Q(company__name__icontains=q)
            )
        if stage and stage in LeadStage.values:
            qs = qs.filter(stage=stage)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stages"] = LeadStage.choices
        ctx["current_stage"] = self.request.GET.get("stage", "")
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class LeadDetailView(CRMBaseView, DetailView):
    model = Lead
    template_name = "crm/lead_detail.html"
    context_object_name = "lead"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["interactions"] = self.object.interactions.select_related("user").order_by("-timestamp")
        ctx["interaction_form"] = InteractionLogForm()
        ctx["all_stages"] = LeadStage.choices
        return ctx


class LeadCreateView(CRMBaseView, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Lead '%s' created successfully.") % self.object.title)
        # Log initial creation
        InteractionLog.objects.create(
            lead=self.object,
            contact=self.object.contact,
            user=self.request.user,
            interaction_type=InteractionType.NOTE,
            summary=_("Lead created"),
            details=_("Initial lead creation in stage: %s") % self.object.get_stage_display(),
        )
        return response

    def get_success_url(self):
        return reverse("crm:lead_detail", kwargs={"pk": self.object.pk})


class LeadUpdateView(CRMBaseView, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Lead '%s' updated successfully.") % self.object.title)
        return response

    def get_success_url(self):
        return reverse("crm:lead_detail", kwargs={"pk": self.object.pk})


class LeadDeleteView(CRMBaseView, DeleteView):
    model = Lead
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:lead_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        title = obj.title
        res = super().delete(request, *args, **kwargs)
        messages.success(request, _("Lead '%s' deleted successfully.") % title)
        return res


class LeadAddInteractionView(CRMBaseView, View):
    """POST view to append a note, call, meeting or email to a lead."""
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        form = InteractionLogForm(request.POST)
        if form.is_valid():
            interaction = form.save(commit=False)
            interaction.lead = lead
            interaction.contact = lead.contact
            interaction.user = request.user
            interaction.save()
            messages.success(request, _("Interaction logged successfully."))
        else:
            messages.error(request, _("Failed to log interaction. Please check the form."))
        return redirect("crm:lead_detail", pk=lead.pk)


# ==============================================================================
# Contact Views
# ==============================================================================

class ContactListView(CRMBaseView, ListView):
    model = Contact
    template_name = "crm/contact_list.html"
    context_object_name = "contacts"
    paginate_by = 20

    def get_queryset(self):
        qs = Contact.objects.select_related("company")
        q = self.request.GET.get("q", "").strip()
        tag = self.request.GET.get("tag", "").strip()

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q) |
                Q(company__name__icontains=q)
            )
        if tag:
            qs = qs.filter(tags__icontains=tag)

        return qs.order_by("last_name", "first_name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "")
        ctx["current_tag"] = self.request.GET.get("tag", "")
        return ctx


class ContactDetailView(CRMBaseView, DetailView):
    model = Contact
    template_name = "crm/contact_detail.html"
    context_object_name = "contact"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["leads"] = self.object.leads.select_related("company", "assigned_to")
        ctx["interactions"] = self.object.interactions.select_related("lead", "user").order_by("-timestamp")
        ctx["enrollments"] = self.object.sequence_enrollments.select_related("sequence")
        ctx["interaction_form"] = InteractionLogForm()
        return ctx


class ContactCreateView(CRMBaseView, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Contact '%s' created successfully.") % self.object.full_name)
        return response

    def get_success_url(self):
        return reverse("crm:contact_detail", kwargs={"pk": self.object.pk})


class ContactUpdateView(CRMBaseView, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Contact '%s' updated successfully.") % self.object.full_name)
        return response

    def get_success_url(self):
        return reverse("crm:contact_detail", kwargs={"pk": self.object.pk})


class ContactDeleteView(CRMBaseView, DeleteView):
    model = Contact
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:contact_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        name = obj.full_name
        res = super().delete(request, *args, **kwargs)
        messages.success(request, _("Contact '%s' deleted successfully.") % name)
        return res


# ==============================================================================
# Company Views
# ==============================================================================

class CompanyListView(CRMBaseView, ListView):
    model = Company
    template_name = "crm/company_list.html"
    context_object_name = "companies"
    paginate_by = 20

    def get_queryset(self):
        qs = Company.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(industry__icontains=q) |
                Q(city__icontains=q) |
                Q(country__icontains=q)
            )
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class CompanyDetailView(CRMBaseView, DetailView):
    model = Company
    template_name = "crm/company_detail.html"
    context_object_name = "company"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["contacts"] = self.object.contacts.all()
        ctx["leads"] = self.object.leads.select_related("contact", "assigned_to")
        return ctx


class CompanyCreateView(CRMBaseView, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = "crm/company_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Company '%s' created successfully.") % self.object.name)
        return response

    def get_success_url(self):
        return reverse("crm:company_detail", kwargs={"pk": self.object.pk})


class CompanyUpdateView(CRMBaseView, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "crm/company_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Company '%s' updated successfully.") % self.object.name)
        return response

    def get_success_url(self):
        return reverse("crm:company_detail", kwargs={"pk": self.object.pk})


class CompanyDeleteView(CRMBaseView, DeleteView):
    model = Company
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:company_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        name = obj.name
        res = super().delete(request, *args, **kwargs)
        messages.success(request, _("Company '%s' deleted successfully.") % name)
        return res


# ==============================================================================
# 14c — Email Sequences Views
# ==============================================================================

class SequenceListView(CRMBaseView, ListView):
    model = EmailSequence
    template_name = "crm/sequence_list.html"
    context_object_name = "sequences"

    def get_queryset(self):
        return EmailSequence.objects.annotate(
            step_count=Count("steps"),
            enrollment_count=Count("enrollments"),
        ).order_by("name")


class SequenceDetailView(CRMBaseView, DetailView):
    model = EmailSequence
    template_name = "crm/sequence_detail.html"
    context_object_name = "sequence"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["steps"] = self.object.steps.order_by("step_number")
        ctx["enrollments"] = self.object.enrollments.select_related("contact", "lead")[:25]
        ctx["step_form"] = EmailStepForm()
        return ctx


class SequenceCreateView(CRMBaseView, CreateView):
    model = EmailSequence
    form_class = EmailSequenceForm
    template_name = "crm/sequence_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Sequence '%s' created successfully.") % self.object.name)
        return response

    def get_success_url(self):
        return reverse("crm:sequence_detail", kwargs={"pk": self.object.pk})


class SequenceUpdateView(CRMBaseView, UpdateView):
    model = EmailSequence
    form_class = EmailSequenceForm
    template_name = "crm/sequence_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Sequence '%s' updated successfully.") % self.object.name)
        return response

    def get_success_url(self):
        return reverse("crm:sequence_detail", kwargs={"pk": self.object.pk})


class SequenceDeleteView(CRMBaseView, DeleteView):
    model = EmailSequence
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:sequence_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        name = obj.name
        res = super().delete(request, *args, **kwargs)
        messages.success(request, _("Sequence '%s' deleted successfully.") % name)
        return res


class EmailStepCreateView(CRMBaseView, CreateView):
    model = EmailStep
    form_class = EmailStepForm
    template_name = "crm/step_form.html"

    def form_valid(self, form):
        seq = get_object_or_404(EmailSequence, pk=self.kwargs["pk"])
        form.instance.sequence = seq
        response = super().form_valid(form)
        messages.success(self.request, _("Email step added to '%s'.") % seq.name)
        return response

    def get_success_url(self):
        return reverse("crm:sequence_detail", kwargs={"pk": self.kwargs["pk"]})


class EmailStepUpdateView(CRMBaseView, UpdateView):
    model = EmailStep
    form_class = EmailStepForm
    template_name = "crm/step_form.html"
    pk_url_kwarg = "step_pk"

    def get_queryset(self):
        return EmailStep.objects.filter(sequence_id=self.kwargs["pk"])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Email step updated."))
        return response

    def get_success_url(self):
        return reverse("crm:sequence_detail", kwargs={"pk": self.kwargs["pk"]})


class EmailStepDeleteView(CRMBaseView, DeleteView):
    model = EmailStep
    template_name = "crm/confirm_delete.html"
    pk_url_kwarg = "step_pk"

    def get_queryset(self):
        return EmailStep.objects.filter(sequence_id=self.kwargs["pk"])

    def delete(self, request, *args, **kwargs):
        res = super().delete(request, *args, **kwargs)
        messages.success(request, _("Email step deleted."))
        return res

    def get_success_url(self):
        return reverse("crm:sequence_detail", kwargs={"pk": self.kwargs["pk"]})


class ProcessSequencesNowView(CRMBaseView, View):
    """Triggers the Celery email sequence processor immediately."""
    def post(self, request):
        try:
            result = process_email_sequences.delay()
            task_id = result.id
        except Exception:
            process_email_sequences()
            task_id = "local-sync"

        messages.success(
            request,
            _("Email sequence dispatch task launched (Task ID: %s).") % task_id,
        )
        return redirect(request.POST.get("next") or reverse("crm:sequence_list"))


# ==============================================================================
# 14d — Customer Segmentation Views
# ==============================================================================

class SegmentListView(CRMBaseView, ListView):
    model = Segment
    template_name = "crm/segment_list.html"
    context_object_name = "segments"


class SegmentDetailView(CRMBaseView, DetailView):
    model = Segment
    template_name = "crm/segment_detail.html"
    context_object_name = "segment"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        matching_contacts = self.object.get_matching_contacts()
        ctx["matching_contacts"] = matching_contacts[:50]
        ctx["total_matching_contacts"] = matching_contacts.count()
        ctx["matching_leads"] = self.object.get_matching_leads()[:20]
        ctx["broadcast_form"] = BroadcastEmailForm()
        return ctx


class SegmentCreateView(CRMBaseView, CreateView):
    model = Segment
    form_class = SegmentForm
    template_name = "crm/segment_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Segment '%s' created successfully.") % self.object.name)
        return response

    def get_success_url(self):
        return reverse("crm:segment_detail", kwargs={"pk": self.object.pk})


class SegmentUpdateView(CRMBaseView, UpdateView):
    model = Segment
    form_class = SegmentForm
    template_name = "crm/segment_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Segment '%s' updated successfully.") % self.object.name)
        return response

    def get_success_url(self):
        return reverse("crm:segment_detail", kwargs={"pk": self.object.pk})


class SegmentDeleteView(CRMBaseView, DeleteView):
    model = Segment
    template_name = "crm/confirm_delete.html"
    success_url = reverse_lazy("crm:segment_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        name = obj.name
        res = super().delete(request, *args, **kwargs)
        messages.success(request, _("Segment '%s' deleted successfully.") % name)
        return res


class SegmentBroadcastView(CRMBaseView, View):
    """POST view to trigger a broadcast campaign to all subscribed contacts in a segment."""
    def post(self, request, pk):
        segment = get_object_or_404(Segment, pk=pk)
        form = BroadcastEmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            message_text = form.cleaned_data["message"]
            try:
                result = send_segment_broadcast.delay(
                    segment_id=segment.pk,
                    subject=subject,
                    message=message_text,
                    sender_user_id=request.user.id,
                )
                task_id = result.id
            except Exception:
                send_segment_broadcast(
                    segment_id=segment.pk,
                    subject=subject,
                    message=message_text,
                    sender_user_id=request.user.id,
                )
                task_id = "local-sync"

            messages.success(
                request,
                _("Broadcast campaign launched to segment '%s' (Task ID: %s).") % (segment.name, task_id),
            )
        else:
            messages.error(request, _("Please provide a valid subject and message."))

        return redirect("crm:segment_detail", pk=segment.pk)


# ==============================================================================
# 14e — Analytics Dashboard Views
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
