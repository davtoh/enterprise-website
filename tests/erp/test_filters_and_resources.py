from datetime import date, timedelta

import pytest
from django.contrib import admin
from django.urls import reverse
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from erp.filters import InvoiceFilter, ProductFilter, StockMovementFilter
from erp.models import (
    Invoice,
    InvoiceStatus,
    Product,
    StockMovement,
    StockMovementType,
)
from erp.resources import InvoiceResource, ProductResource, StockMovementResource


@pytest.mark.django_db
class TestERPFiltersAndResources:
    """Verify FilterSets, Import/Export ModelResources, and HTMX partials in ERP."""

    def test_product_filter_search_and_category(self, test_product, test_category):
        Product.objects.create(sku="SKU-OTHER", name="Other Widget")
        qs = ProductFilter(
            {"q": test_product.sku, "category": test_category.pk},
            queryset=Product.objects.all(),
        ).qs
        assert list(qs) == [test_product]

    def test_invoice_filter_status_and_search(self, test_invoice):
        paid = Invoice.objects.create(
            customer_name="Paid Corp",
            customer_email="paid@example.com",
            due_date=date.today() + timedelta(days=7),
            status=InvoiceStatus.PAID,
        )
        qs = InvoiceFilter(
            {"status": InvoiceStatus.PAID, "q": "Paid Corp"},
            queryset=Invoice.objects.all(),
        ).qs
        assert list(qs) == [paid]
        assert test_invoice not in qs

    def test_stock_movement_filter_type_and_search(self, test_product, test_location, auth_user):
        mv_in = StockMovement.objects.create(
            product=test_product,
            location=test_location,
            movement_type=StockMovementType.IN,
            quantity=5,
            reference="PO-999",
            created_by=auth_user,
        )
        StockMovement.objects.create(
            product=test_product,
            location=test_location,
            movement_type=StockMovementType.OUT,
            quantity=1,
            reference="SO-111",
            created_by=auth_user,
        )
        qs = StockMovementFilter(
            {"type": StockMovementType.IN, "q": "PO-999"},
            queryset=StockMovement.objects.all(),
        ).qs
        assert list(qs) == [mv_in]

    def test_erp_resources_export_and_dry_run_import(
        self, test_product, test_invoice, test_location, auth_user
    ):
        mv = StockMovement.objects.create(
            product=test_product,
            location=test_location,
            movement_type=StockMovementType.IN,
            quantity=2,
            reference="RES-TEST",
            created_by=auth_user,
        )
        for resource_cls, qs in (
            (ProductResource, Product.objects.filter(pk=test_product.pk)),
            (InvoiceResource, Invoice.objects.filter(pk=test_invoice.pk)),
            (StockMovementResource, StockMovement.objects.filter(pk=mv.pk)),
        ):
            resource = resource_cls()
            dataset = resource.export(qs)
            assert len(dataset) == 1
            result = resource.import_data(dataset, dry_run=True)
            assert not result.has_errors()

    def test_erp_admin_uses_unfold_and_import_export(self):
        for model in (Product, Invoice, StockMovement):
            model_admin = admin.site._registry[model]
            assert isinstance(model_admin, UnfoldModelAdmin)
            assert isinstance(model_admin, ImportExportModelAdmin)

    def test_erp_list_views_htmx_partial_rendering(
        self, client, auth_user, test_product, test_invoice, test_location
    ):
        StockMovement.objects.create(
            product=test_product,
            location=test_location,
            movement_type=StockMovementType.IN,
            quantity=3,
            reference="HTMX-REF-1",
            created_by=auth_user,
        )
        client.force_login(auth_user)
        for url_name, query, expected_text in (
            ("erp:product_list", test_product.sku, test_product.name),
            ("erp:movement_list", "HTMX-REF-1", "HTMX-REF-1"),
            ("erp:invoice_list", test_invoice.invoice_number, test_invoice.invoice_number),
        ):
            resp = client.get(
                reverse(url_name),
                {"q": query},
                headers={"HX-Request": "true"},
            )
            assert resp.status_code == 200
            html = resp.content.decode("utf-8")
            assert expected_text in html
            assert "<html" not in html.lower()
