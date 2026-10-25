import datetime
import json
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from erp.models import (
    Category,
    InventoryLocation,
    Product,
    StockMovement,
    StockMovementType,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
)
from erp.forms import (
    ProductForm,
    CategoryForm,
    InventoryLocationForm,
    StockMovementForm,
    InvoiceForm,
)
from erp.pdf import generate_invoice_pdf
from erp.tasks import check_low_stock_alerts, send_invoice_email
from erp.utils import get_erp_dashboard_metrics, get_erp_chart_data
from erp.plugin import (
    ERPPlugin,
    ERPProcurementPlugin,
    ERPWarehousePlugin,
    ERPAccountingPlugin,
)
from plugin_registry import registry

User = get_user_model()


@pytest.fixture
def auth_user(db):
    return User.objects.create_user(
        username="erp_manager",
        email="manager@enterprise.local",
        password="SecurePassword123!",
        is_staff=True,
    )


@pytest.fixture
def test_category(db):
    return Category.objects.create(
        name="Industrial Hardware",
        description="Heavy-duty enterprise machinery and robotics parts",
    )


@pytest.fixture
def test_location(db):
    return InventoryLocation.objects.create(
        name="Main Central Depot",
        code="DEPOT-01",
        address="100 Enterprise Way, Industrial Park",
        is_active=True,
    )


@pytest.fixture
def test_product(db, test_category):
    return Product.objects.create(
        sku="ROBOT-ARM-01",
        name="Robotic Articulated Arm",
        category=test_category,
        description="High precision 6-axis articulated industrial robotic arm",
        unit="unit",
        unit_price=Decimal("4500.00"),
        cost_price=Decimal("2800.00"),
        current_stock=25,
        reorder_threshold=10,
        is_active=True,
    )


@pytest.fixture
def test_invoice(db, auth_user, test_product):
    inv = Invoice.objects.create(
        customer_name="Apex Robotics Corp",
        customer_email="procurement@apexrobotics.io",
        customer_address="500 Innovation Blvd, Silicon Hills",
        issue_date=datetime.date.today(),
        due_date=datetime.date.today() + datetime.timedelta(days=30),
        status=InvoiceStatus.DRAFT,
        tax_rate=Decimal("10.00"),
        discount_amount=Decimal("100.00"),
        created_by=auth_user,
    )
    InvoiceItem.objects.create(
        invoice=inv,
        product=test_product,
        description="Robotic Articulated Arm Unit",
        quantity=Decimal("2.00"),
        unit_price=Decimal("4500.00"),
    )
    return inv


# =========================================================================
# Model Tests
# =========================================================================

@pytest.mark.django_db
def test_category_creation_and_slug(test_category):
    assert test_category.slug == "industrial-hardware"
    assert str(test_category) == "Industrial Hardware"


@pytest.mark.django_db
def test_location_creation_and_str(test_location):
    assert str(test_location) == "Main Central Depot (DEPOT-01)"
    assert test_location.is_active is True


@pytest.mark.django_db
def test_product_properties_and_calculations(test_product):
    assert test_product.slug == "robotic-articulated-arm"
    assert str(test_product) == "Robotic Articulated Arm (ROBOT-ARM-01)"
    assert test_product.is_low_stock is False
    assert test_product.stock_value == Decimal("112500.00")
    assert test_product.cost_value == Decimal("70000.00")
    assert test_product.margin == Decimal("1700.00")


@pytest.mark.django_db
def test_stock_movement_in_updates_current_stock(test_product, test_location, auth_user):
    initial_stock = test_product.current_stock
    StockMovement.objects.create(
        product=test_product,
        location=test_location,
        movement_type=StockMovementType.IN,
        quantity=15,
        reference="PO-9901",
        created_by=auth_user,
    )
    test_product.refresh_from_db()
    assert test_product.current_stock == initial_stock + 15


@pytest.mark.django_db
def test_stock_movement_out_decrements_current_stock(test_product, test_location, auth_user):
    initial_stock = test_product.current_stock
    StockMovement.objects.create(
        product=test_product,
        location=test_location,
        movement_type=StockMovementType.OUT,
        quantity=5,
        reference="INV-1002",
        created_by=auth_user,
    )
    test_product.refresh_from_db()
    assert test_product.current_stock == initial_stock - 5


@pytest.mark.django_db
def test_stock_movement_return_and_adjustment(test_product, test_location, auth_user):
    # Customer return (+ quantity)
    StockMovement.objects.create(
        product=test_product,
        location=test_location,
        movement_type=StockMovementType.RETURN,
        quantity=3,
        reference="RET-001",
        created_by=auth_user,
    )
    test_product.refresh_from_db()
    assert test_product.current_stock == 28

    # Audit adjustment (-8 discrepancy)
    StockMovement.objects.create(
        product=test_product,
        location=test_location,
        movement_type=StockMovementType.ADJUSTMENT,
        quantity=-8,
        reference="AUDIT-2026",
        created_by=auth_user,
    )
    test_product.refresh_from_db()
    assert test_product.current_stock == 20


@pytest.mark.django_db
def test_invoice_and_item_totals_calculation(test_invoice):
    # Initial: 2 units @ $4500 = $9,000 subtotal
    # Tax: 10% of $9000 = $900
    # Discount: $100
    # Total: $9,000 + $900 - $100 = $9,800
    test_invoice.refresh_from_db()
    assert test_invoice.subtotal == Decimal("9000.00")
    assert test_invoice.tax_amount == Decimal("900.00")
    assert test_invoice.total_amount == Decimal("9800.00")
    assert test_invoice.invoice_number.startswith("INV-")

    # Add second item
    InvoiceItem.objects.create(
        invoice=test_invoice,
        description="Warranty Support Plan",
        quantity=Decimal("1.00"),
        unit_price=Decimal("1000.00"),
    )
    test_invoice.refresh_from_db()
    # New subtotal: $10,000
    # Tax: 10% = $1,000
    # Total: $10,000 + $1,000 - $100 = $10,900
    assert test_invoice.subtotal == Decimal("10000.00")
    assert test_invoice.tax_amount == Decimal("1000.00")
    assert test_invoice.total_amount == Decimal("10900.00")


# =========================================================================
# PDF Generation Tests
# =========================================================================

@pytest.mark.django_db
def test_generate_invoice_pdf(test_invoice):
    pdf_bytes = generate_invoice_pdf(test_invoice)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


# =========================================================================
# Celery Tasks Tests
# =========================================================================

@pytest.mark.django_db
def test_check_low_stock_alerts(test_product):
    # Set current stock below threshold
    test_product.current_stock = 4
    test_product.save(update_fields=["current_stock"])

    result = check_low_stock_alerts()
    assert result["status"] == "success"
    assert result["low_stock_count"] >= 1
    flagged_skus = [i["sku"] for i in result["flagged_items"]]
    assert test_product.sku in flagged_skus


@pytest.mark.django_db
def test_send_invoice_email_task(test_invoice):
    assert test_invoice.status == InvoiceStatus.DRAFT

    result = send_invoice_email(test_invoice.pk)
    assert result["status"] == "success"
    assert result["recipient"] == test_invoice.customer_email

    # Check status transitioned to SENT
    test_invoice.refresh_from_db()
    assert test_invoice.status == InvoiceStatus.SENT

    # Check mail outbox
    assert len(mail.outbox) >= 1
    sent_mail = mail.outbox[-1]
    assert test_invoice.customer_email in sent_mail.to
    assert len(sent_mail.attachments) == 1
    assert sent_mail.attachments[0][0].endswith(".pdf")


# =========================================================================
# Analytics & Utils Tests
# =========================================================================

@pytest.mark.django_db
def test_erp_dashboard_metrics(test_product, test_invoice):
    metrics = get_erp_dashboard_metrics()
    assert metrics["total_products"] >= 1
    assert metrics["stock_value"] > Decimal("0.00")
    assert metrics["outstanding_invoices_count"] >= 1
    assert metrics["outstanding_amount"] > Decimal("0.00")


@pytest.mark.django_db
def test_erp_chart_data(test_product, test_invoice):
    chart_data = get_erp_chart_data()
    assert "revenue_trend" in chart_data
    assert len(chart_data["revenue_trend"]["labels"]) == 6
    assert "top_products" in chart_data
    assert test_product.name in chart_data["top_products"]["labels"]
    assert "inventory_levels" in chart_data


# =========================================================================
# Views & HTTP Endpoints Tests
# =========================================================================

@pytest.mark.django_db
def test_dashboard_view(client, auth_user, test_product, test_invoice, test_location):
    StockMovement.objects.create(
        product=test_product,
        location=test_location,
        movement_type=StockMovementType.IN,
        quantity=5,
        reference="INIT-01",
        created_by=auth_user,
    )
    client.force_login(auth_user)
    response = client.get(reverse("erp:dashboard"))
    assert response.status_code == 200
    assert "Enterprise ERP" in response.content.decode()
    assert test_product.name in response.content.decode()
    assert test_invoice.invoice_number in response.content.decode()


@pytest.mark.django_db
def test_inventory_dashboard_view(client, auth_user, test_product):
    client.force_login(auth_user)
    response = client.get(reverse("erp:inventory_dashboard"))
    assert response.status_code == 200
    assert test_product.name in response.content.decode()

    # Test filtering by query
    response_q = client.get(reverse("erp:inventory_dashboard") + f"?q={test_product.sku}")
    assert response_q.status_code == 200
    assert test_product.sku in response_q.content.decode()


@pytest.mark.django_db
def test_product_crud_views(client, auth_user, test_category):
    client.force_login(auth_user)

    # 1. Create Product
    create_url = reverse("erp:product_create")
    post_data = {
        "sku": "CNC-LATHE-X1",
        "name": "Precision CNC Lathe X1",
        "category": test_category.pk,
        "unit": "unit",
        "unit_price": "12500.00",
        "cost_price": "8900.00",
        "current_stock": 5,
        "reorder_threshold": 2,
        "is_active": True,
    }
    create_resp = client.post(create_url, post_data)
    assert create_resp.status_code == 302
    created_product = Product.objects.get(sku="CNC-LATHE-X1")

    # 2. Detail View
    detail_resp = client.get(reverse("erp:product_detail", kwargs={"pk": created_product.pk}))
    assert detail_resp.status_code == 200
    assert "Precision CNC Lathe X1" in detail_resp.content.decode()

    # 3. Update View
    update_url = reverse("erp:product_update", kwargs={"pk": created_product.pk})
    post_data["name"] = "Precision CNC Lathe X1 Pro"
    update_resp = client.post(update_url, post_data)
    assert update_resp.status_code == 302
    created_product.refresh_from_db()
    assert created_product.name == "Precision CNC Lathe X1 Pro"

    # 4. Delete View
    del_url = reverse("erp:product_delete", kwargs={"pk": created_product.pk})
    del_resp = client.post(del_url)
    assert del_resp.status_code == 302
    assert not Product.objects.filter(pk=created_product.pk).exists()


@pytest.mark.django_db
def test_stock_movement_views(client, auth_user, test_product, test_location):
    client.force_login(auth_user)

    # List view
    list_resp = client.get(reverse("erp:movement_list"))
    assert list_resp.status_code == 200

    # Create view
    initial_stock = test_product.current_stock
    create_url = reverse("erp:movement_create")
    post_data = {
        "product": test_product.pk,
        "location": test_location.pk,
        "movement_type": StockMovementType.IN,
        "quantity": 10,
        "reference": "PO-TEST-123",
        "notes": "Incoming replenishment",
    }
    create_resp = client.post(create_url, post_data)
    assert create_resp.status_code == 302

    test_product.refresh_from_db()
    assert test_product.current_stock == initial_stock + 10


@pytest.mark.django_db
def test_invoice_views(client, auth_user, test_invoice):
    client.force_login(auth_user)

    # 1. Invoice list
    list_resp = client.get(reverse("erp:invoice_list"))
    assert list_resp.status_code == 200
    assert test_invoice.invoice_number in list_resp.content.decode()

    # 2. Invoice detail
    detail_resp = client.get(reverse("erp:invoice_detail", kwargs={"pk": test_invoice.pk}))
    assert detail_resp.status_code == 200
    assert test_invoice.customer_name in detail_resp.content.decode()

    # 3. Invoice PDF view
    pdf_resp = client.get(reverse("erp:invoice_pdf", kwargs={"pk": test_invoice.pk}))
    assert pdf_resp.status_code == 200
    assert pdf_resp["Content-Type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")

    # 4. Status update
    status_resp = client.post(
        reverse("erp:invoice_status_update", kwargs={"pk": test_invoice.pk, "new_status": "PAID"})
    )
    assert status_resp.status_code == 302
    test_invoice.refresh_from_db()
    assert test_invoice.status == InvoiceStatus.PAID

    # 5. Email invoice view
    email_resp = client.post(reverse("erp:invoice_send_email", kwargs={"pk": test_invoice.pk}))
    assert email_resp.status_code == 302

    # 6. Invoice Create View (GET & POST)
    get_create_resp = client.get(reverse("erp:invoice_create"))
    assert get_create_resp.status_code == 200

    post_invoice_data = {
        "customer_name": "Nexus Corp",
        "customer_email": "billing@nexuscorp.local",
        "customer_address": "123 Tech Way",
        "issue_date": str(datetime.date.today()),
        "due_date": str(datetime.date.today() + datetime.timedelta(days=15)),
        "status": InvoiceStatus.DRAFT,
        "tax_rate": "5.00",
        "discount_amount": "0.00",
        "notes": "Net 15",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-description": "Engineering Consulting",
        "items-0-quantity": "10.00",
        "items-0-unit_price": "150.00",
    }
    create_post_resp = client.post(reverse("erp:invoice_create"), post_invoice_data)
    assert create_post_resp.status_code == 302
    nexus_invoice = Invoice.objects.get(customer_name="Nexus Corp")
    assert nexus_invoice.total_amount == Decimal("1575.00")

    # 7. Invoice Update View (GET & POST)
    get_update_resp = client.get(reverse("erp:invoice_update", kwargs={"pk": nexus_invoice.pk}))
    assert get_update_resp.status_code == 200

    item_id = nexus_invoice.items.first().pk
    post_invoice_data.update({
        "customer_name": "Nexus Corporation Global",
        "items-INITIAL_FORMS": "1",
        "items-0-id": str(item_id),
        "items-0-invoice": str(nexus_invoice.pk),
    })
    update_post_resp = client.post(reverse("erp:invoice_update", kwargs={"pk": nexus_invoice.pk}), post_invoice_data)
    assert update_post_resp.status_code == 302
    nexus_invoice.refresh_from_db()
    assert nexus_invoice.customer_name == "Nexus Corporation Global"

    # 8. Invoice Delete View
    del_resp = client.post(reverse("erp:invoice_delete", kwargs={"pk": nexus_invoice.pk}))
    assert del_resp.status_code == 302
    assert not Invoice.objects.filter(pk=nexus_invoice.pk).exists()


@pytest.mark.django_db
def test_analytics_data_api(client, auth_user, test_invoice):
    client.force_login(auth_user)
    resp = client.get(reverse("erp:analytics_data"))
    assert resp.status_code == 200
    data = json.loads(resp.content)
    assert "revenue_trend" in data
    assert "top_products" in data
    assert "inventory_levels" in data


@pytest.mark.django_db
def test_modules_overview_view(client, auth_user):
    client.force_login(auth_user)
    resp = client.get(reverse("erp:modules_overview"))
    assert resp.status_code == 200
    assert "ERP Modular Architecture" in resp.content.decode()
    assert "erp_procurement" in resp.content.decode()
    assert "erp_warehouse" in resp.content.decode()
    assert "erp_accounting" in resp.content.decode()


# =========================================================================
# Plugin Registry Integration Tests
# =========================================================================

def test_erp_plugins_discovery_in_registry():
    registry.autodiscover()
    plugins = registry.get_all_plugins()

    assert "erp" in plugins
    erp_plugin = plugins["erp"]
    assert issubclass(erp_plugin, ERPPlugin)
    assert erp_plugin.name == "erp"
    assert len(erp_plugin.get_menu_items()) == 1
    assert erp_plugin.get_menu_items()[0].url_name == "erp:dashboard"

    # Future sub-module stubs
    assert "erp_procurement" in plugins
    proc_plugin = plugins["erp_procurement"]
    assert getattr(proc_plugin, "is_stub", False) is True
    assert getattr(proc_plugin, "status", "") == "coming_soon"

    assert "erp_warehouse" in plugins
    wh_plugin = plugins["erp_warehouse"]
    assert getattr(wh_plugin, "is_stub", False) is True

    assert "erp_accounting" in plugins
    acc_plugin = plugins["erp_accounting"]
    assert getattr(acc_plugin, "is_stub", False) is True
