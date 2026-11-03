import json
from decimal import Decimal
import pytest
from django.urls import reverse

from erp.models import StockMovement, StockMovementType
from erp.plugin import (
    ERPAccountingPlugin,
    ERPPlugin,
    ERPProcurementPlugin,
    ERPWarehousePlugin,
)
from erp.utils import get_erp_chart_data, get_erp_dashboard_metrics
from plugin_registry import registry


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

