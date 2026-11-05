from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
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
from ..forms import EmailSequenceForm, EmailStepForm
from ..models import EmailSequence, EmailStep
from ..tasks import process_email_sequences


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

