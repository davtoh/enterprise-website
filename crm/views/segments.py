from django.contrib import messages
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
from ..forms import SegmentForm, BroadcastEmailForm
from ..models import Segment
from ..tasks import send_segment_broadcast


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

