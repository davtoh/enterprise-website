import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views import View

from erp.models import (
    Category,
    Invoice,
    Product,
    StockMovement,
)
from erp.utils import get_erp_chart_data, get_erp_dashboard_metrics

logger = logging.getLogger(__name__)


FUTURE_SUBMODULES = [
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

        context = {
            "metrics": metrics,
            "recent_movements": recent_movements,
            "recent_invoices": recent_invoices,
            "low_stock_products": low_stock_products,
            "submodules": FUTURE_SUBMODULES,
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


class AnalyticsDataApiView(LoginRequiredMixin, View):
    """API endpoint providing real-time data for Chart.js dashboard charts."""

    def get(self, request):
        data = get_erp_chart_data()
        return JsonResponse(data)


class ModulesOverviewView(LoginRequiredMixin, View):
    """Architecture overview page detailing the ERP core and modular pluggable extensions."""

    def get(self, request):
        return render(request, "erp/modules_overview.html")
