"""
ERP Views Package — Modular View Subsystem.

Decomposed from monolithic erp/views.py (439 lines) into domain submodules:
- dashboard.py: DashboardView, InventoryDashboardView, AnalyticsDataApiView, ModulesOverviewView
- products.py: ProductListView, ProductDetailView, ProductCreateView, ProductUpdateView, ProductDeleteView
- inventory.py: StockMovementListView, StockMovementCreateView
- invoices.py: InvoiceListView, InvoiceDetailView, InvoiceCreateView, InvoiceUpdateView, InvoiceDeleteView,
              InvoiceStatusUpdateView, InvoicePdfDownloadView, InvoiceSendEmailView
"""

import logging

from .dashboard import (
    DashboardView,
    InventoryDashboardView,
    AnalyticsDataApiView,
    ModulesOverviewView,
)
from .products import (
    ProductListView,
    ProductDetailView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
)
from .inventory import (
    StockMovementListView,
    StockMovementCreateView,
)
from .invoices import (
    InvoiceListView,
    InvoiceDetailView,
    InvoiceCreateView,
    InvoiceUpdateView,
    InvoiceDeleteView,
    InvoiceStatusUpdateView,
    InvoicePdfDownloadView,
    InvoiceSendEmailView,
)

logger = logging.getLogger(__name__)

__all__ = [
    # Dashboard & Inventory control
    "DashboardView",
    "InventoryDashboardView",
    "AnalyticsDataApiView",
    "ModulesOverviewView",
    # Products catalog
    "ProductListView",
    "ProductDetailView",
    "ProductCreateView",
    "ProductUpdateView",
    "ProductDeleteView",
    # Stock movements
    "StockMovementListView",
    "StockMovementCreateView",
    # Invoices & billing
    "InvoiceListView",
    "InvoiceDetailView",
    "InvoiceCreateView",
    "InvoiceUpdateView",
    "InvoiceDeleteView",
    "InvoiceStatusUpdateView",
    "InvoicePdfDownloadView",
    "InvoiceSendEmailView",
    # Logger
    "logger",
]

