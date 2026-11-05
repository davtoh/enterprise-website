import datetime
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model

from erp.models import (
    Category,
    InventoryLocation,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Product,
)

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

