from django.urls import path
from . import views

app_name = "erp"

urlpatterns = [
    # Dashboard & Inventory control
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("inventory/", views.InventoryDashboardView.as_view(), name="inventory_dashboard"),

    # Products catalog CRUD
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/create/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),

    # Stock movements
    path("movements/", views.StockMovementListView.as_view(), name="movement_list"),
    path("movements/create/", views.StockMovementCreateView.as_view(), name="movement_create"),

    # Invoices & billing
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/create/", views.InvoiceCreateView.as_view(), name="invoice_create"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.InvoiceUpdateView.as_view(), name="invoice_update"),
    path("invoices/<int:pk>/delete/", views.InvoiceDeleteView.as_view(), name="invoice_delete"),
    path("invoices/<int:pk>/status/<str:new_status>/", views.InvoiceStatusUpdateView.as_view(), name="invoice_status_update"),
    path("invoices/<int:pk>/pdf/", views.InvoicePdfDownloadView.as_view(), name="invoice_pdf"),
    path("invoices/<int:pk>/send-email/", views.InvoiceSendEmailView.as_view(), name="invoice_send_email"),

    # Analytics API & Modular Architecture stubs
    path("analytics/data/", views.AnalyticsDataApiView.as_view(), name="analytics_data"),
    path("modules/", views.ModulesOverviewView.as_view(), name="modules_overview"),
]
