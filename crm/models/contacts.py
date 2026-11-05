import re
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .companies import Company


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
        from .leads import InteractionLog, InteractionType
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
        from .leads import InteractionLog, InteractionType
        InteractionLog.objects.create(
            contact=self,
            interaction_type=InteractionType.SECURITY_ACCESS,
            summary=summary,
            details=details,
        )
        return True

