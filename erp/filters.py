import django_filters
from django.db.models import Q

from .models import (
    Category,
    Invoice,
    InvoiceStatus,
    Product,
    StockMovement,
    StockMovementType,
)


class ProductFilter(django_filters.FilterSet):
    """Declarative FilterSet for ERP Product list views and API endpoints."""

    q = django_filters.CharFilter(method="filter_search")
    category = django_filters.ModelChoiceFilter(
        field_name="category",
        queryset=Category.objects.all(),
    )

    class Meta:
        model = Product
        fields = ["category", "is_active"]

    def filter_search(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        return queryset.filter(Q(name__icontains=term) | Q(sku__icontains=term))


class InvoiceFilter(django_filters.FilterSet):
    """Declarative FilterSet for ERP Invoice list views and API endpoints."""

    q = django_filters.CharFilter(method="filter_search")
    status = django_filters.ChoiceFilter(
        field_name="status",
        choices=InvoiceStatus.choices,
    )

    class Meta:
        model = Invoice
        fields = ["status"]

    def filter_search(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        return queryset.filter(
            Q(invoice_number__icontains=term)
            | Q(customer_name__icontains=term)
            | Q(customer_email__icontains=term)
        )


class StockMovementFilter(django_filters.FilterSet):
    """Declarative FilterSet for ERP StockMovement list views and API endpoints."""

    q = django_filters.CharFilter(method="filter_search")
    type = django_filters.ChoiceFilter(
        field_name="movement_type",
        choices=StockMovementType.choices,
    )

    class Meta:
        model = StockMovement
        fields = ["type", "location"]

    def filter_search(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        return queryset.filter(
            Q(product__name__icontains=term)
            | Q(product__sku__icontains=term)
            | Q(reference__icontains=term)
        )
