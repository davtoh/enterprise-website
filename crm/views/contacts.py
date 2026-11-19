from django.contrib import messages
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .base import CRMBaseView
from ..filters import ContactFilter
from ..forms import ContactForm, InteractionLogForm
from ..models import Contact


class ContactListView(CRMBaseView, ListView):
    model = Contact
    template_name = "crm/contact_list.html"
    partial_template_name = "crm/partials/contact_table.html"
    context_object_name = "contacts"
    paginate_by = 20

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return [self.partial_template_name]
        return [self.template_name]

    def get_queryset(self):
        base_qs = Contact.objects.select_related(
            "company", "last_seen_location"
        ).order_by("last_name", "first_name")
        self.filterset = ContactFilter(self.request.GET, queryset=base_qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = getattr(self, "filterset", None)
        ctx["query"] = self.request.GET.get("q", "")
        ctx["current_tag"] = self.request.GET.get("tag", "")
        ctx["current_clearance"] = self.request.GET.get("clearance", "")
        ctx["current_presence"] = self.request.GET.get("presence", "")
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
        ctx["access_logs"] = self.object.access_logs.select_related("site").order_by("-timestamp")[:10]
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

