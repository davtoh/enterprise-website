from django.utils.translation import gettext_lazy as _
from plugin_registry.base import AppPlugin, MenuItemDefinition


class ERPPlugin(AppPlugin):
    """Core ERP plugin providing Product catalog, Inventory tracking, and Invoicing."""

    name = "erp"
    verbose_name = _("Enterprise Resource Planning (ERP)")
    description = _(
        "Lightweight ERP core with product catalog, inventory tracking, "
        "invoice PDF generation, and executive financial metrics."
    )
    category = "management"
    icon = "fa fa-cubes"

    url_namespace = "erp"
    url_prefix = "erp"

    menu_items = [
        MenuItemDefinition(
            label=_("ERP"),
            url_name="erp:dashboard",
            icon="fa fa-cubes",
            order=33,
            parent_slug="Apps",
            requires_auth=True,
        ),
    ]

    tasks = [
        "erp.check_low_stock_alerts",
        "erp.send_invoice_email",
    ]


class ERPProcurementPlugin(AppPlugin):
    """Sub-module stub: Purchase orders, vendor management, and receiving logs."""

    name = "erp_procurement"
    verbose_name = _("ERP: Procurement & Suppliers")
    description = _(
        "Supplier relationship management, purchase orders (PO), vendor pricing agreements, "
        "and incoming shipment inspection and receiving."
    )
    category = "management"
    icon = "fa fa-truck"
    is_stub = True
    status = "coming_soon"


class ERPWarehousePlugin(AppPlugin):
    """Sub-module stub: Multi-location stock tracking, bin management, and transfers."""

    name = "erp_warehouse"
    verbose_name = _("ERP: Advanced Warehousing")
    description = _(
        "Multi-facility warehouse topology, bin and aisle mapping, inter-warehouse stock transfer "
        "workflows, and batch/lot/serial number tracing."
    )
    category = "management"
    icon = "fa fa-building-o"
    is_stub = True
    status = "coming_soon"


class ERPAccountingPlugin(AppPlugin):
    """Sub-module stub: Full general ledger, double-entry bookkeeping, and reporting."""

    name = "erp_accounting"
    verbose_name = _("ERP: General Ledger & Accounting")
    description = _(
        "Double-entry bookkeeping engine, customizable chart of accounts, accounts payable/receivable, "
        "trial balance, and automated P&L / balance sheet generation."
    )
    category = "management"
    icon = "fa fa-calculator"
    is_stub = True
    status = "coming_soon"
