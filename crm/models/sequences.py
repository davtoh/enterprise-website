import uuid
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .contacts import Contact
from .leads import Lead, LeadStage


# ==============================================================================
# 14c — Email Sequences Models
# ==============================================================================

class EmailSequence(models.Model):
    """Automated drip campaign sequence containing one or more scheduled steps."""
    name = models.CharField(max_length=200, verbose_name=_("Sequence Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    trigger_stage = models.CharField(
        max_length=30,
        choices=[("", _("Manual Enrollment Only"))] + LeadStage.choices,
        blank=True,
        default="",
        verbose_name=_("Auto-Enroll On Stage Entry"),
        help_text=_("When a lead moves to this stage, automatically enroll primary contact."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("When inactive, scheduled emails in this sequence will be skipped."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Email Sequence")
        verbose_name_plural = _("Email Sequences")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("crm:sequence_detail", kwargs={"pk": self.pk})

    @property
    def total_steps(self) -> int:
        return self.steps.count()

    @property
    def active_enrollments_count(self) -> int:
        return self.enrollments.filter(status=SequenceEnrollmentStatus.ACTIVE).count()


class EmailStep(models.Model):
    """A single scheduled email in a drip sequence."""
    sequence = models.ForeignKey(
        EmailSequence,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name=_("Email Sequence"),
    )
    step_number = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Step Number"),
    )
    delay_days = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Delay (Days)"),
        help_text=_("Days to wait after enrollment or previous step before sending."),
    )
    subject = models.CharField(max_length=255, verbose_name=_("Email Subject"))
    body_template = models.TextField(
        verbose_name=_("Email Body (Template)"),
        help_text=_(
            "Supports placeholders: {{ contact.first_name }}, {{ contact.last_name }}, "
            "{{ contact.email }}, {{ company.name }}, {{ lead.title }}, {{ tracking_pixel }}"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Email Step")
        verbose_name_plural = _("Email Steps")
        ordering = ["sequence", "step_number"]
        unique_together = ("sequence", "step_number")

    def __str__(self):
        return f"{self.sequence.name} — Step {self.step_number}: {self.subject}"


class SequenceEnrollmentStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    COMPLETED = "completed", _("Completed")
    PAUSED = "paused", _("Paused")
    CANCELLED = "cancelled", _("Cancelled")


class SequenceEnrollment(models.Model):
    """Tracks a contact's progress through an automated email sequence."""
    sequence = models.ForeignKey(
        EmailSequence,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name=_("Sequence"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="sequence_enrollments",
        verbose_name=_("Contact"),
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sequence_enrollments",
        verbose_name=_("Associated Lead"),
    )
    current_step_number = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Current Step Number"),
    )
    status = models.CharField(
        max_length=20,
        choices=SequenceEnrollmentStatus.choices,
        default=SequenceEnrollmentStatus.ACTIVE,
        verbose_name=_("Status"),
    )
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Enrolled At"))
    next_send_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_("Next Send Scheduled At"),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At"),
    )

    class Meta:
        verbose_name = _("Sequence Enrollment")
        verbose_name_plural = _("Sequence Enrollments")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.contact.full_name} in {self.sequence.name} (Step {self.current_step_number})"


class EmailDeliveryStatus(models.TextChoices):
    SENT = "sent", _("Sent")
    OPENED = "opened", _("Opened")
    FAILED = "failed", _("Failed")


class EmailDeliveryLog(models.Model):
    """Record of individual outbound emails sent by sequences or campaigns."""
    enrollment = models.ForeignKey(
        SequenceEnrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_logs",
        verbose_name=_("Sequence Enrollment"),
    )
    step = models.ForeignKey(
        EmailStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_logs",
        verbose_name=_("Email Step"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="delivery_logs",
        verbose_name=_("Recipient Contact"),
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_logs",
        verbose_name=_("Associated Lead"),
    )
    recipient_email = models.EmailField(verbose_name=_("Recipient Email"))
    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    tracking_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Tracking Token"),
    )
    status = models.CharField(
        max_length=20,
        choices=EmailDeliveryStatus.choices,
        default=EmailDeliveryStatus.SENT,
        db_index=True,
        verbose_name=_("Delivery Status"),
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Sent At"))
    opened_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Opened At"),
    )
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))

    class Meta:
        verbose_name = _("Email Delivery Log")
        verbose_name_plural = _("Email Delivery Logs")
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.subject} -> {self.recipient_email} [{self.get_status_display()}]"

    def record_opened(self):
        if self.status != EmailDeliveryStatus.OPENED:
            self.status = EmailDeliveryStatus.OPENED
            self.opened_at = timezone.now()
            self.save(update_fields=["status", "opened_at"])

