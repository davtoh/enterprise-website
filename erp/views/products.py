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

from erp.forms import ProductForm
from erp.models import Category, Product

logger = logging.getLogger(__name__)


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "erp/product_list.html"
    context_object_name = "products"
    paginate_by = 15

    def get_queryset(self):
        qs = Product.objects.select_related("category").order_by("name")
        q = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
        if category:
            qs = qs.filter(category_id=category)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
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

