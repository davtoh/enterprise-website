"""
ERP Modular Test Package.
Decomposed from monolithic tests/test_erp.py (522 lines):
- conftest.py: Shared fixtures (auth_user, test_category, test_location, test_product, test_invoice)
- test_dashboard_and_analytics.py: Dashboard KPIs, Chart.js telemetry, modular plugins discovery
- test_products_and_inventory.py: Product model/CRUD, stock movement ledger, low-stock Celery task
- test_invoices_and_pdf.py: Invoice calculations, ReportLab PDF rendering, email dispatch, invoice CRUD
"""

