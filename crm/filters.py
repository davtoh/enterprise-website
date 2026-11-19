import django_filters
from django.db.models import Q

from .models import (
    Company,
    Contact,
    Lead,
    LeadSource,
    LeadStage,
    PresenceStatus,
    SecurityClearance,
)


class CompanyFilter(django_filters.FilterSet):
    """Declarative FilterSet for CRM Company list views and API endpoints."""

    q = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Company
        fields = ["industry", "country"]

    def filter_search(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        return queryset.filter(
            Q(name__icontains=term)
            | Q(industry__icontains=term)
            | Q(city__icontains=term)
            | Q(country__icontains=term)
        )


class ContactFilter(django_filters.FilterSet):
    """Declarative FilterSet for CRM Contact list views and API endpoints."""

    q = django_filters.CharFilter(method="filter_search")
    tag = django_filters.CharFilter(field_name="tags", lookup_expr="icontains")
    clearance = django_filters.ChoiceFilter(
        field_name="security_clearance",
        choices=SecurityClearance.choices,
    )
    presence = django_filters.ChoiceFilter(
        field_name="presence_status",
        choices=PresenceStatus.choices,
    )

    class Meta:
        model = Contact
        fields = ["clearance", "presence", "tag", "is_subscribed"]

    def filter_search(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        return queryset.filter(
            Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(email__icontains=term)
            | Q(company__name__icontains=term)
            | Q(license_plate__icontains=term)
            | Q(security_tag__icontains=term)
        )


class LeadFilter(django_filters.FilterSet):
    """Declarative FilterSet for CRM Lead list views and API endpoints."""

    q = django_filters.CharFilter(method="filter_search")
    stage = django_filters.ChoiceFilter(field_name="stage", choices=LeadStage.choices)
    source = django_filters.ChoiceFilter(field_name="source", choices=LeadSource.choices)

    class Meta:
        model = Lead
        fields = ["stage", "source", "assigned_to"]

    def filter_search(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        return queryset.filter(
            Q(title__icontains=term)
            | Q(contact__first_name__icontains=term)
            | Q(contact__last_name__icontains=term)
            | Q(company__name__icontains=term)
        )
