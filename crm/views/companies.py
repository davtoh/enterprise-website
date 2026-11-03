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
from ..forms import CompanyForm
from ..models import Company


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

