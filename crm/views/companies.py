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
from ..filters import CompanyFilter
from ..forms import CompanyForm
from ..models import Company


class CompanyListView(CRMBaseView, ListView):
    model = Company
    template_name = "crm/company_list.html"
    partial_template_name = "crm/partials/company_table.html"
    context_object_name = "companies"
    paginate_by = 20

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return [self.partial_template_name]
        return [self.template_name]

    def get_queryset(self):
        base_qs = Company.objects.all().order_by("name")
        self.filterset = CompanyFilter(self.request.GET, queryset=base_qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = getattr(self, "filterset", None)
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

