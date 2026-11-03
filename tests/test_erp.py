"""
Test Suite Facade: ERP Subsystem.

Backward-compatible re-export module routing tests to focused domain test modules in `tests/erp/`:
- `test_dashboard_and_analytics`: Dashboard KPIs, Chart.js telemetry, modular plugins discovery.
- `test_products_and_inventory`: Product model/CRUD, stock movement ledger, low-stock Celery task.
- `test_invoices_and_pdf`: Invoice calculations, ReportLab PDF rendering, email dispatch, invoice CRUD.
"""

from .erp.conftest import (
    auth_user,
    test_category,
    test_location,
    test_product,
    test_invoice,
)

from .erp.test_dashboard_and_analytics import (
    test_erp_dashboard_metrics,
    test_erp_chart_data,
    test_dashboard_view,
    test_inventory_dashboard_view,
    test_analytics_data_api,
    test_modules_overview_view,
    test_erp_plugins_discovery_in_registry,
)

from .erp.test_products_and_inventory import (
    test_category_creation_and_slug,
    test_location_creation_and_str,
    test_product_properties_and_calculations,
    test_stock_movement_in_updates_current_stock,
    test_stock_movement_out_decrements_current_stock,
    test_stock_movement_return_and_adjustment,
    test_check_low_stock_alerts,
    test_product_crud_views,
    test_stock_movement_views,
)

from .erp.test_invoices_and_pdf import (
    test_invoice_and_item_totals_calculation,
    test_generate_invoice_pdf,
    test_send_invoice_email_task,
    test_invoice_views,
)
