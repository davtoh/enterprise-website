from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .base import CRMBaseView
from ..forms import LeadForm, InteractionLogForm
from ..models import Lead, LeadStage, InteractionLog, InteractionType


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

