import datetime
from decimal import Decimal
from django.db.models import F, Sum
from django.utils import timezone
from .models import Product, Invoice, InvoiceStatus, StockMovement


def get_erp_dashboard_metrics() -> dict:
    """
    Computes key executive metrics for the ERP core module:
    - Product catalog volume
    - Inventory valuation
    - Revenue metrics (monthly & lifetime)
    - Outstanding invoices and receivables
    - Low-stock alert count
    """
    now = timezone.now()
    active_products = Product.objects.filter(is_active=True)
    total_products = active_products.count()

    # Total valuation of on-hand inventory
    stock_value = sum((p.stock_value for p in active_products), Decimal("0.00"))
    cost_value = sum((p.cost_value for p in active_products), Decimal("0.00"))

    # Low stock items
    low_stock_products = active_products.filter(current_stock__lte=F("reorder_threshold"))
    low_stock_count = low_stock_products.count()

    # Revenue metrics
    current_year = now.year
    current_month = now.month

    monthly_paid_invoices = Invoice.objects.filter(
        status=InvoiceStatus.PAID,
        issue_date__year=current_year,
        issue_date__month=current_month,
    )
    monthly_revenue = monthly_paid_invoices.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

    total_revenue = Invoice.objects.filter(
        status=InvoiceStatus.PAID
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

    # Outstanding invoices (DRAFT, SENT, OVERDUE)
    outstanding_qs = Invoice.objects.filter(
        status__in=[InvoiceStatus.DRAFT, InvoiceStatus.SENT, InvoiceStatus.OVERDUE]
    )
    outstanding_invoices_count = outstanding_qs.count()
    outstanding_amount = outstanding_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

    return {
        "total_products": total_products,
        "stock_value": stock_value,
        "cost_value": cost_value,
        "low_stock_count": low_stock_count,
        "monthly_revenue": monthly_revenue,
        "total_revenue": total_revenue,
        "outstanding_invoices_count": outstanding_invoices_count,
        "outstanding_amount": outstanding_amount,
    }


def get_erp_chart_data() -> dict:
    """
    Generates structured JSON chart datasets for vendored Chart.js:
    - 6-month historical revenue trend
    - Top 5 products by stock valuation
    - Inventory levels vs reorder thresholds
    """
    now = timezone.now()

    # 1. Monthly Revenue Trend (Last 6 Months)
    revenue_labels = []
    revenue_values = []

    for i in range(5, -1, -1):
        # Calculate target month and year
        month_idx = now.month - i
        year = now.year
        while month_idx <= 0:
            month_idx += 12
            year -= 1

        dt = datetime.date(year, month_idx, 1)
        month_label = dt.strftime("%b %Y")
        revenue_labels.append(month_label)

        month_sum = Invoice.objects.filter(
            status=InvoiceStatus.PAID,
            issue_date__year=year,
            issue_date__month=month_idx,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        revenue_values.append(float(month_sum))

    # 2. Top Products by Stock Value
    products = list(Product.objects.filter(is_active=True))
    products_sorted = sorted(products, key=lambda p: p.stock_value, reverse=True)[:5]
    top_product_labels = [p.name for p in products_sorted] or ["No Products"]
    top_product_values = [float(p.stock_value) for p in products_sorted] or [0.0]

    # 3. Inventory Stock Levels (Top 6 Items)
    top_stock_items = sorted(products, key=lambda p: p.current_stock, reverse=True)[:6]
    stock_item_labels = [p.name for p in top_stock_items] or ["No Stock"]
    stock_current_values = [p.current_stock for p in top_stock_items] or [0]
    stock_threshold_values = [p.reorder_threshold for p in top_stock_items] or [0]

    return {
        "revenue_trend": {
            "labels": revenue_labels,
            "data": revenue_values,
        },
        "top_products": {
            "labels": top_product_labels,
            "data": top_product_values,
        },
        "inventory_levels": {
            "labels": stock_item_labels,
            "current": stock_current_values,
            "threshold": stock_threshold_values,
        },
    }
