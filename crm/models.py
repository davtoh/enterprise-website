import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone
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


class SecurityClearance(models.TextChoices):
    VIP = "VIP", _("VIP Access")
    STAFF = "STAFF", _("Staff Member")
    CONTRACTOR = "CONTRACTOR", _("Contractor")
    VISITOR = "VISITOR", _("Visitor Pass")
    RESTRICTED = "RESTRICTED", _("Restricted / Escort Required")
    BANNED = "BANNED", _("Banned / Denied Entry")


class PresenceStatus(models.TextChoices):
    OFF_PREMISES = "off_premises", _("Off-Premises")
    ON_PREMISES = "on_premises", _("On-Premises / Checked In")


class Contact(models.Model):
    """An individual person associated with companies and deals."""
    first_name = models.CharField(max_length=120, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=120, verbose_name=_("Last Name"))
    email = models.EmailField(unique=True, verbose_name=_("Email Address"))
    phone = models.CharField(max_length=50, blank=True, verbose_name=_("Phone Number"))
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name=_("Company"),
    )
    job_title = models.CharField(max_length=150, blank=True, verbose_name=_("Job Title"))
    is_subscribed = models.BooleanField(
        default=True,
        verbose_name=_("Subscribed to Marketing"),
        help_text=_("Designates whether this contact receives marketing broadcast emails."),
    )
    tags = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Tags"),
        help_text=_("Comma-separated tags (e.g. enterprise, vip, inbound, lead)."),
    )
    # Physical Security & Edge AI Access Credentials (Milestone 16d / Phase E4)
    security_clearance = models.CharField(
        max_length=25,
        choices=SecurityClearance.choices,
        default=SecurityClearance.VISITOR,
        blank=True,
        db_index=True,
        verbose_name=_("Security Clearance"),
        help_text=_("Physical site security clearance and access level."),
    )
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Access Valid From"),
        help_text=_("Start of validity window for temporary guest or contractor pass."),
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Access Valid Until"),
        help_text=_("Expiration timestamp for temporary visitor passes."),
    )
    license_plate = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        verbose_name=_("Vehicle License Plate"),
        help_text=_("Vehicle license plate for automated gate ANPR recognition."),
    )
    face_profile_photo = models.ImageField(
        upload_to="crm/faces/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("Biometric Profile Photo"),
        help_text=_("Reference photo for edge face recognition vector generation."),
    )
    face_embedding_vector = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Biometric Embedding Vector"),
        help_text=_("Pre-computed 512-d biometric embedding for zero-latency edge startup."),
    )
    security_tag = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name=_("Security Classification Tag"),
        help_text=_("Custom classification tag for edge tracker classification (e.g. exec-zone, server-room)."),
    )
    presence_status = models.CharField(
        max_length=25,
        choices=PresenceStatus.choices,
        default=PresenceStatus.OFF_PREMISES,
        blank=True,
        db_index=True,
        verbose_name=_("Presence Status"),
        help_text=_("Real-time physical presence status at facilities."),
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Last Seen At"),
    )
    last_seen_location = models.ForeignKey(
        "location_management.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="present_contacts",
        verbose_name=_("Last Seen Location"),
    )

    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("crm:contact_detail", kwargs={"pk": self.pk})

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def is_pass_valid(self) -> bool:
        """
        Determines whether the physical security pass is currently valid.
        Returns False if clearance is BANNED or current time falls outside [valid_from, valid_until].
        """
        if self.security_clearance == SecurityClearance.BANNED:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    @property
    def normalized_license_plate(self) -> str:
        """Returns normalized uppercase alphanumeric license plate."""
        if not self.license_plate:
            return ""
        import re
        return re.sub(r"[^A-Z0-9]", "", self.license_plate.upper())

    @property
    def clearance_badge_class(self) -> str:
        mapping = {
            SecurityClearance.VIP: "warning text-dark",
            SecurityClearance.STAFF: "success",
            SecurityClearance.CONTRACTOR: "info text-dark",
            SecurityClearance.VISITOR: "primary",
            SecurityClearance.RESTRICTED: "danger",
            SecurityClearance.BANNED: "dark",
        }
        return mapping.get(self.security_clearance, "secondary")

    @property
    def presence_badge_class(self) -> str:
        return "success" if self.presence_status == PresenceStatus.ON_PREMISES else "secondary"

    def check_in(self, location=None, verification_method="face", gate_camera_id=None, notes="") -> bool:
        """
        Marks contact as on-premises, updates last seen location/timestamp,
        and creates an InteractionLog entry.
        """
        self.presence_status = PresenceStatus.ON_PREMISES
        self.last_seen_at = timezone.now()
        if location:
            self.last_seen_location = location
        self.save(update_fields=["presence_status", "last_seen_at", "last_seen_location", "updated_at"])

        # Auto-create audit entry in InteractionLog
        loc_name = str(location) if location else _("Gate")
        method_label = verification_method.capitalize()
        summary = f"Physical Gate Access (Entry): {loc_name} via {method_label}"
        details = notes or f"Contact checked in at {loc_name}. Camera: {gate_camera_id or 'N/A'}."
        InteractionLog.objects.create(
            contact=self,
            interaction_type=InteractionType.SECURITY_ACCESS,
            summary=summary,
            details=details,
        )
        return True

    def check_out(self, location=None, verification_method="face", gate_camera_id=None, notes="") -> bool:
        """
        Marks contact as off-premises, updates last seen location/timestamp,
        and creates an InteractionLog entry.
        """
        self.presence_status = PresenceStatus.OFF_PREMISES
        self.last_seen_at = timezone.now()
        if location:
            self.last_seen_location = location
        self.save(update_fields=["presence_status", "last_seen_at", "last_seen_location", "updated_at"])

        loc_name = str(location) if location else _("Gate")
        method_label = verification_method.capitalize()
        summary = f"Physical Gate Access (Exit): {loc_name} via {method_label}"
        details = notes or f"Contact checked out at {loc_name}. Camera: {gate_camera_id or 'N/A'}."
        InteractionLog.objects.create(
            contact=self,
            interaction_type=InteractionType.SECURITY_ACCESS,
            summary=summary,
            details=details,
        )
        return True


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
        if note:
            details = note
        else:
            details = f"Lead moved to {self.get_stage_display()} stage."

        InteractionLog.objects.create(
            lead=self,
            contact=self.contact,
            user=user if (user and user.is_authenticated) else None,
            interaction_type=InteractionType.STAGE_CHANGE,
            summary=summary,
            details=details,
        )

        # Trigger sequence enrollment for the new stage
        from .utils import auto_enroll_lead_in_sequences
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
