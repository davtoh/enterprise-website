import logging
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
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

from .models import (
    Product,
    Category,
    InventoryLocation,
    StockMovement,
    StockMovementType,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
)
from .forms import (
    ProductForm,
    CategoryForm,
    InventoryLocationForm,
    StockMovementForm,
    InvoiceForm,
    InvoiceItemFormSet,
)
from .pdf import generate_invoice_pdf
from .tasks import send_invoice_email
from .utils import get_erp_dashboard_metrics, get_erp_chart_data

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, View):
    """Main executive ERP dashboard displaying KPIs, Chart.js trends, and modular stubs."""

    def get(self, request):
        metrics = get_erp_dashboard_metrics()
        recent_movements = StockMovement.objects.select_related("product", "location")[:8]
        recent_invoices = Invoice.objects.all()[:8]
        low_stock_products = Product.objects.filter(
            is_active=True,
            current_stock__lte=F("reorder_threshold"),
        ).select_related("category")[:5]

        # Modular future sub-module definitions
        submodules = [
            {
                "name": "erp_procurement",
                "title": _("Procurement & Purchase Orders"),
                "icon": "fa fa-truck",
                "badge": _("Modular Extension"),
                "status": "coming_soon",
                "description": _(
                    "Supplier relationship management, request for quotes (RFQ), "
                    "purchase orders (PO), vendor catalog price lists, and receiving docks."
                ),
                "features": [
                    _("Vendor management & evaluation"),
                    _("Purchase order generation & approvals"),
                    _("Shipment receiving & automatic stock intake"),
                ],
            },
            {
                "name": "erp_warehouse",
                "title": _("Advanced Multi-Location Warehouse"),
                "icon": "fa fa-building-o",
                "badge": _("Modular Extension"),
                "status": "coming_soon",
                "description": _(
                    "Multi-warehouse spatial topology, bin/aisle/shelf tracking, "
                    "inter-warehouse transfer orders, and lot/serial number traceability."
                ),
                "features": [
                    _("Multi-warehouse & bin locations"),
                    _("Inter-location stock transfer requisitions"),
                    _("Lot & serial tracking for traceability"),
                ],
            },
            {
                "name": "erp_accounting",
                "title": _("General Ledger & Full Accounting"),
                "icon": "fa fa-calculator",
                "badge": _("Modular Extension"),
                "status": "coming_soon",
                "description": _(
                    "Complete double-entry bookkeeping engine with custom chart of accounts, "
                    "journal entries, accounts payable/receivable, trial balance, and P&L."
                ),
                "features": [
                    _("Double-entry journal ledger"),
                    _("Automated Balance Sheet & Income Statement"),
                    _("Accounts payable & receivable reconciliation"),
                ],
            },
        ]

        context = {
            "metrics": metrics,
            "recent_movements": recent_movements,
            "recent_invoices": recent_invoices,
            "low_stock_products": low_stock_products,
            "submodules": submodules,
        }
        return render(request, "erp/dashboard.html", context)


class InventoryDashboardView(LoginRequiredMixin, View):
    """Inventory control dashboard with stock levels, low-stock warnings, and quick filters."""

    def get(self, request):
        metrics = get_erp_dashboard_metrics()
        q = request.GET.get("q", "").strip()
        category_id = request.GET.get("category", "").strip()
        low_stock_only = request.GET.get("low_stock", "").strip()

        products = Product.objects.filter(is_active=True).select_related("category")
        if q:
            products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
        if category_id:
            products = products.filter(category_id=category_id)
        if low_stock_only == "1":
            products = products.filter(current_stock__lte=F("reorder_threshold"))

        categories = Category.objects.all()
        recent_movements = StockMovement.objects.select_related("product", "location")[:10]

        context = {
            "metrics": metrics,
            "products": products,
            "categories": categories,
            "recent_movements": recent_movements,
            "search_query": q,
            "selected_category": category_id,
            "low_stock_only": low_stock_only == "1",
        }
        return render(request, "erp/inventory_dashboard.html", context)


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


class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = "erp/movement_list.html"
    context_object_name = "movements"
    paginate_by = 20

    def get_queryset(self):
        qs = StockMovement.objects.select_related("product", "location", "created_by").order_by("-created_at")
        mtype = self.request.GET.get("type", "").strip()
        q = self.request.GET.get("q", "").strip()
        if mtype:
            qs = qs.filter(movement_type=mtype)
        if q:
            qs = qs.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q) | Q(reference__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["movement_types"] = StockMovementType.choices
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class StockMovementCreateView(LoginRequiredMixin, View):
    """Record a stock movement and auto-update inventory on-hand balance."""

    def get(self, request):
        initial_product = request.GET.get("product")
        form = StockMovementForm(initial={"product": initial_product} if initial_product else None)
        return render(request, "erp/movement_form.html", {"form": form})

    def post(self, request):
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            movement.save()
            messages.success(
                request,
                _("Stock movement recorded: %(type)s %(qty)s for %(product)s.")
                % {
                    "type": movement.get_movement_type_display(),
                    "qty": movement.quantity,
                    "product": movement.product.name,
                },
            )
            return redirect("erp:inventory_dashboard")
        return render(request, "erp/movement_form.html", {"form": form})


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "erp/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 15

    def get_queryset(self):
        qs = Invoice.objects.order_by("-issue_date", "-id")
        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(Q(invoice_number__icontains=q) | Q(customer_name__icontains=q) | Q(customer_email__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = InvoiceStatus.choices
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "erp/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["items"] = self.object.items.select_related("product").all()
        return ctx


class InvoiceCreateView(LoginRequiredMixin, View):
    """Create invoice along with line items via formset."""

    def get(self, request):
        form = InvoiceForm()
        formset = InvoiceItemFormSet()
        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset})

    def post(self, request):
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.created_by = request.user
                invoice.save()

                formset.instance = invoice
                formset.save()

                invoice.recalculate_totals()

            messages.success(request, _("Invoice %(number)s created successfully.") % {"number": invoice.invoice_number})
            return redirect("erp:invoice_detail", pk=invoice.pk)

        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset})


class InvoiceUpdateView(LoginRequiredMixin, View):
    """Edit invoice and line items."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)
        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset, "invoice": invoice})

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save()
                formset.save()
                invoice.recalculate_totals()

            messages.success(request, _("Invoice %(number)s updated successfully.") % {"number": invoice.invoice_number})
            return redirect("erp:invoice_detail", pk=invoice.pk)

        return render(request, "erp/invoice_form.html", {"form": form, "formset": formset, "invoice": invoice})


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Invoice
    template_name = "erp/confirm_delete.html"
    success_url = reverse_lazy("erp:invoice_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Invoice deleted successfully."))
        return super().delete(request, *args, **kwargs)


class InvoiceStatusUpdateView(LoginRequiredMixin, View):
    """Quick transition of invoice status (e.g. mark as PAID, CANCELLED, SENT)."""

    def post(self, request, pk, new_status):
        invoice = get_object_or_404(Invoice, pk=pk)
        if new_status in InvoiceStatus.values:
            invoice.status = new_status
            invoice.save(update_fields=["status", "updated_at"])
            messages.success(
                request,
                _("Invoice %(number)s marked as %(status)s.")
                % {"number": invoice.invoice_number, "status": invoice.get_status_display()},
            )
        return redirect("erp:invoice_detail", pk=invoice.pk)


class InvoicePdfDownloadView(LoginRequiredMixin, View):
    """Generate and stream or download the PDF invoice."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        pdf_bytes = generate_invoice_pdf(invoice)

        filename = f"{invoice.invoice_number or 'invoice'}.pdf"
        disposition = "attachment" if request.GET.get("download") == "1" else "inline"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response


class InvoiceSendEmailView(LoginRequiredMixin, View):
    """Send invoice PDF as email attachment to the customer."""

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            # Attempt Celery task execution, falling back to sync execution if broker unavailable
            try:
                send_invoice_email.delay(invoice.pk)
            except Exception as task_err:
                logger.info("Celery broker unavailable, executing send_invoice_email synchronously: %s", task_err)
                send_invoice_email(invoice.pk)

            messages.success(
                request,
                _("Invoice PDF email dispatched to %(email)s.") % {"email": invoice.customer_email},
            )
        except Exception as exc:
            logger.error("Failed sending invoice email: %s", exc)
            messages.error(request, _("Error delivering invoice email: %(err)s") % {"err": str(exc)})

        return redirect("erp:invoice_detail", pk=invoice.pk)


class AnalyticsDataApiView(LoginRequiredMixin, View):
    """API endpoint providing real-time data for Chart.js dashboard charts."""

    def get(self, request):
        data = get_erp_chart_data()
        return JsonResponse(data)


class ModulesOverviewView(LoginRequiredMixin, View):
    """Architecture overview page detailing the ERP core and modular pluggable extensions."""

    def get(self, request):
        return render(request, "erp/modules_overview.html")
