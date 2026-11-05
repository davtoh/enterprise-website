from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .companies import Company
from .contacts import Contact


class LeadStage(models.TextChoices):
    NEW = "new", _("New")
    CONTACTED = "contacted", _("Contacted")
    QUALIFIED = "qualified", _("Qualified")
    PROPOSAL = "proposal", _("Proposal")
    WON = "won", _("Won")
    LOST = "lost", _("Lost")


class LeadSource(models.TextChoices):
    WEBSITE = "website", _("Website Form")
    REFERRAL = "referral", _("Referral")
    COLD_OUTREACH = "cold_outreach", _("Cold Outreach")
    INBOUND_EMAIL = "inbound_email", _("Inbound Email")
    EVENT = "event", _("Event / Conference")
    OTHER = "other", _("Other")


class Lead(models.Model):
    """A sales opportunity or prospective deal tracking through the pipeline."""
    title = models.CharField(max_length=255, verbose_name=_("Deal / Lead Title"))
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        verbose_name=_("Primary Contact"),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        verbose_name=_("Company"),
    )
    stage = models.CharField(
        max_length=30,
        choices=LeadStage.choices,
        default=LeadStage.NEW,
        db_index=True,
        verbose_name=_("Pipeline Stage"),
    )
    source = models.CharField(
        max_length=40,
        choices=LeadSource.choices,
        default=LeadSource.WEBSITE,
        verbose_name=_("Lead Source"),
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Estimated Value ($)"),
    )
    expected_close_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Expected Close Date"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_crm_leads",
        verbose_name=_("Assigned Sales Rep"),
    )
    notes = models.TextField(blank=True, verbose_name=_("Deal Notes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Lead / Deal")
        verbose_name_plural = _("Leads / Deals")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_stage_display()})"

    def get_absolute_url(self):
        return reverse("crm:lead_detail", kwargs={"pk": self.pk})

    def change_stage(self, new_stage: str, user=None, note: str = "") -> bool:
        """
        Transitions lead to a new pipeline stage and logs the event automatically
        to InteractionLog. Also triggers automatic sequence enrollments.
        """
        if new_stage not in LeadStage.values:
            raise ValueError(f"Invalid lead stage: {new_stage}")

        if self.stage == new_stage:
            return False

        old_stage_display = self.get_stage_display()
        self.stage = new_stage
        self.save(update_fields=["stage", "updated_at"])

        # Auto-create audit entry in InteractionLog
        summary = f"Stage changed from '{old_stage_display}' to '{self.get_stage_display()}'"
        details = note if note else f"Lead moved to {self.get_stage_display()} stage."

        InteractionLog.objects.create(
            lead=self,
            contact=self.contact,
            user=user if (user and user.is_authenticated) else None,
            interaction_type=InteractionType.STAGE_CHANGE,
            summary=summary,
            details=details,
        )

        # Trigger sequence enrollment for the new stage
        from crm.utils import auto_enroll_lead_in_sequences
        auto_enroll_lead_in_sequences(self)

        return True


class InteractionType(models.TextChoices):
    NOTE = "note", _("Note")
    CALL = "call", _("Phone Call")
    EMAIL = "email", _("Email")
    MEETING = "meeting", _("Meeting")
    STAGE_CHANGE = "stage_change", _("Stage Change")
    SEQUENCE_STEP = "sequence_step", _("Sequence Drip Step")
    BROADCAST = "broadcast", _("Broadcast Campaign")
    SECURITY_ACCESS = "security_access", _("Physical Security Access")


class InteractionLog(models.Model):
    """Chronological activity and touchpoint history for contacts and deals."""
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="interactions",
        verbose_name=_("Associated Lead / Deal"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="interactions",
        verbose_name=_("Associated Contact"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_interactions",
        verbose_name=_("Staff User"),
    )
    interaction_type = models.CharField(
        max_length=30,
        choices=InteractionType.choices,
        default=InteractionType.NOTE,
        verbose_name=_("Interaction Type"),
    )
    summary = models.CharField(max_length=255, verbose_name=_("Summary"))
    details = models.TextField(blank=True, verbose_name=_("Details / Notes"))
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_("Timestamp"),
    )

    class Meta:
        verbose_name = _("Interaction Log")
        verbose_name_plural = _("Interaction Logs")
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.get_interaction_type_display()}] {self.summary}"

