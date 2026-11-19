import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from erp.filters import ProductFilter
from erp.forms import ProductForm
from erp.models import Category, Product

logger = logging.getLogger(__name__)


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "erp/product_list.html"
    partial_template_name = "erp/partials/product_table.html"
    context_object_name = "products"
    paginate_by = 15

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return [self.partial_template_name]
        return [self.template_name]

    def get_queryset(self):
        base_qs = Product.objects.select_related("category").order_by("name")
        self.filterset = ProductFilter(self.request.GET, queryset=base_qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = getattr(self, "filterset", None)
        ctx["categories"] = Category.objects.all()
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["selected_category"] = self.request.GET.get("category", "")
        return ctx


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = "erp/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["movements"] = self.object.stock_movements.select_related("location", "created_by")[:20]
        ctx["invoice_items"] = self.object.invoice_items.select_related("invoice")[:10]
        return ctx


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "erp/product_form.html"

    def form_valid(self, form):
        messages.success(self.request, _("Product created successfully."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("erp:product_detail", kwargs={"pk": self.object.pk})


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "erp/product_form.html"

    def form_valid(self, form):
        messages.success(self.request, _("Product updated successfully."))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("erp:product_detail", kwargs={"pk": self.object.pk})


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = "erp/confirm_delete.html"
    success_url = reverse_lazy("erp:product_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Product deleted successfully."))
        return super().delete(request, *args, **kwargs)

