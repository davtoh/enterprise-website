from decimal import Decimal
import pytest
from django.urls import reverse

from erp.models import (
    Product,
    StockMovement,
    StockMovementType,
)
from erp.tasks import check_low_stock_alerts


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

