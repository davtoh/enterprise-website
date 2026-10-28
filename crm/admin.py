from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    Company,
    Contact,
    Lead,
    InteractionLog,
    EmailSequence,
    EmailStep,
    SequenceEnrollment,
    EmailDeliveryLog,
    Segment,
)


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    fields = ("first_name", "last_name", "email", "phone", "job_title", "is_subscribed")
    show_change_link = True


class InteractionLogInline(admin.TabularInline):
    model = InteractionLog
    extra = 0
    fields = ("timestamp", "interaction_type", "summary", "user")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)
    show_change_link = True


class EmailStepInline(admin.StackedInline):
    model = EmailStep
    extra = 1
    fields = ("step_number", "delay_days", "subject", "body_template")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "city", "country", "annual_revenue", "created_at")
    search_fields = ("name", "industry", "city", "country")
    list_filter = ("industry", "country")
    inlines = [ContactInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "company",
        "clearance_badge",
        "presence_badge",
        "license_plate",
        "is_pass_valid_display",
        "is_subscribed",
        "created_at",
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "company__name",
        "license_plate",
        "security_tag",
        "tags",
    )
    list_filter = (
        "security_clearance",
        "presence_status",
        "is_subscribed",
        "company",
    )
    inlines = [InteractionLogInline]

    @admin.display(description=_("Clearance"))
    def clearance_badge(self, obj):
        colors = {
            "VIP": "warning",
            "STAFF": "success",
            "CONTRACTOR": "info",
            "VISITOR": "primary",
            "RESTRICTED": "danger",
            "BANNED": "dark",
        }
        color = colors.get(obj.security_clearance, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_security_clearance_display(),
        )

    @admin.display(description=_("Presence"))
    def presence_badge(self, obj):
        if obj.presence_status == "on_premises":
            return format_html('<span class="badge bg-success">{}</span>', _("On-Premises"))
        return format_html('<span class="badge bg-secondary">{}</span>', _("Off-Premises"))

    @admin.display(description=_("Pass Valid"), boolean=True)
    def is_pass_valid_display(self, obj):
        return obj.is_pass_valid



@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("title", "contact", "company", "stage_badge", "value", "assigned_to", "expected_close_date", "created_at")
    search_fields = ("title", "contact__first_name", "contact__last_name", "company__name")
    list_filter = ("stage", "source", "assigned_to")
    inlines = [InteractionLogInline]

    @admin.display(description=_("Stage"))
    def stage_badge(self, obj):
        colors = {
            "new": "info",
            "contacted": "primary",
            "qualified": "warning",
            "proposal": "secondary",
            "won": "success",
            "lost": "danger",
        }
        color = colors.get(obj.stage, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_stage_display(),
        )


@admin.register(InteractionLog)
class InteractionLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "type_badge", "summary", "lead", "contact", "user")
    search_fields = ("summary", "details", "contact__email", "lead__title")
    list_filter = ("interaction_type", "timestamp", "user")
    readonly_fields = ("timestamp",)

    @admin.display(description=_("Type"))
    def type_badge(self, obj):
        colors = {
            "note": "secondary",
            "call": "info",
            "email": "primary",
            "meeting": "warning",
            "stage_change": "dark",
            "sequence_step": "success",
            "broadcast": "danger",
            "security_access": "info",
        }
        color = colors.get(obj.interaction_type, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_interaction_type_display(),
        )


@admin.register(EmailSequence)
class EmailSequenceAdmin(admin.ModelAdmin):
    list_display = ("name", "trigger_stage", "is_active", "steps_count", "created_at")
    list_filter = ("is_active", "trigger_stage")
    search_fields = ("name", "description")
    inlines = [EmailStepInline]

    @admin.display(description=_("Steps"))
    def steps_count(self, obj):
        return obj.steps.count()


@admin.register(EmailStep)
class EmailStepAdmin(admin.ModelAdmin):
    list_display = ("sequence", "step_number", "delay_days", "subject", "created_at")
    list_filter = ("sequence",)
    search_fields = ("subject", "body_template")


@admin.register(SequenceEnrollment)
class SequenceEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("contact", "sequence", "lead", "current_step_number", "status", "next_send_at", "enrolled_at")
    list_filter = ("status", "sequence")
    search_fields = ("contact__email", "contact__first_name", "contact__last_name", "lead__title")


@admin.register(EmailDeliveryLog)
class EmailDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_email", "subject", "status_badge", "sent_at", "opened_at")
    list_filter = ("status", "sent_at")
    search_fields = ("recipient_email", "subject", "error_message")
    readonly_fields = ("tracking_token", "sent_at", "opened_at")

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colors = {
            "sent": "primary",
            "opened": "success",
            "failed": "danger",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display(),
        )


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_count_display", "lead_count_display", "created_at")
    search_fields = ("name", "description")

    @admin.display(description=_("Matching Contacts"))
    def contact_count_display(self, obj):
        return obj.contact_count

    @admin.display(description=_("Matching Leads"))
    def lead_count_display(self, obj):
        return obj.lead_count
