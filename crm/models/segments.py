from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .contacts import Contact
from .leads import Lead


# ==============================================================================
# 14d — Customer Segmentation Model
# ==============================================================================

class Segment(models.Model):
    """
    Dynamic customer segment defined by declarative JSON filtering rules.
    Example rules:
      {"stage": "qualified", "country": "US", "min_value": 5000, "tag": "enterprise"}
    """
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Segment Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    filter_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Filter Rules (JSON)"),
        help_text=_(
            "Filters applied to contacts/leads. Supported keys: 'stage' (e.g. 'qualified'), "
            "'country' (e.g. 'US'), 'tag' (e.g. 'enterprise'), 'min_value' (number), 'subscribed' (bool)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Customer Segment")
        verbose_name_plural = _("Customer Segments")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("crm:segment_detail", kwargs={"pk": self.pk})

    def get_matching_contacts(self):
        """Evaluates filter rules dynamically against the Contact model."""
        rules = self.filter_rules or {}
        qs = Contact.objects.all()

        if rules.get("subscribed") is True or rules.get("subscribed") == "true":
            qs = qs.filter(is_subscribed=True)
        elif rules.get("subscribed") is False or rules.get("subscribed") == "false":
            qs = qs.filter(is_subscribed=False)

        if rules.get("tag"):
            qs = qs.filter(tags__icontains=str(rules["tag"]).strip())

        if rules.get("country"):
            country_val = str(rules["country"]).strip()
            qs = qs.filter(
                Q(company__country__iexact=country_val) |
                Q(company__city__iexact=country_val)
            )

        if rules.get("industry"):
            qs = qs.filter(company__industry__iexact=str(rules["industry"]).strip())

        if rules.get("stage"):
            stage_val = str(rules["stage"]).strip().lower()
            qs = qs.filter(leads__stage=stage_val)

        if rules.get("min_value") is not None:
            try:
                min_val = Decimal(str(rules["min_value"]))
                qs = qs.filter(leads__value__gte=min_val)
            except Exception:
                pass

        return qs.distinct()

    def get_matching_leads(self):
        """Evaluates filter rules dynamically against the Lead model."""
        rules = self.filter_rules or {}
        qs = Lead.objects.all()

        if rules.get("stage"):
            qs = qs.filter(stage=str(rules["stage"]).strip().lower())

        if rules.get("country"):
            country_val = str(rules["country"]).strip()
            qs = qs.filter(
                Q(company__country__iexact=country_val) |
                Q(company__city__iexact=country_val)
            )

        if rules.get("tag"):
            qs = qs.filter(contact__tags__icontains=str(rules["tag"]).strip())

        if rules.get("min_value") is not None:
            try:
                min_val = Decimal(str(rules["min_value"]))
                qs = qs.filter(value__gte=min_val)
            except Exception:
                pass

        return qs.distinct()

    @property
    def contact_count(self) -> int:
        return self.get_matching_contacts().count()

    @property
    def lead_count(self) -> int:
        return self.get_matching_leads().count()

