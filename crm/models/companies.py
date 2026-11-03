from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """Business organization or client account in the CRM."""
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Company Name"))
    industry = models.CharField(max_length=100, blank=True, verbose_name=_("Industry"))
    website = models.URLField(blank=True, verbose_name=_("Website"))
    phone = models.CharField(max_length=50, blank=True, verbose_name=_("Phone"))
    address = models.TextField(blank=True, verbose_name=_("Address"))
    city = models.CharField(max_length=100, blank=True, verbose_name=_("City"))
    country = models.CharField(max_length=100, blank=True, verbose_name=_("Country"))
    annual_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Annual Revenue ($)"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("crm:company_detail", kwargs={"pk": self.pk})

    @property
    def total_pipeline_value(self) -> Decimal:
        aggregate = self.leads.aggregate(total=Sum("value"))["total"]
        return aggregate or Decimal("0.00")

