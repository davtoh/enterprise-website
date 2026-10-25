from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Company,
    Contact,
    Lead,
    InteractionLog,
    EmailSequence,
    EmailStep,
    Segment,
)


class BaseBootstrapForm(forms.ModelForm):
    """Base form that applies Bootstrap 5 control classes automatically."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.setdefault("class", "form-select")
            elif not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault("class", "form-control")


class CompanyForm(BaseBootstrapForm):
    class Meta:
        model = Company
        fields = [
            "name",
            "industry",
            "website",
            "phone",
            "city",
            "country",
            "annual_revenue",
            "address",
            "notes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ContactForm(BaseBootstrapForm):
    class Meta:
        model = Contact
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "company",
            "job_title",
            "is_subscribed",
            "tags",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class LeadForm(BaseBootstrapForm):
    class Meta:
        model = Lead
        fields = [
            "title",
            "contact",
            "company",
            "stage",
            "source",
            "value",
            "expected_close_date",
            "assigned_to",
            "notes",
        ]
        widgets = {
            "expected_close_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class InteractionLogForm(BaseBootstrapForm):
    class Meta:
        model = InteractionLog
        fields = ["interaction_type", "summary", "details"]
        widgets = {
            "details": forms.Textarea(attrs={"rows": 3, "placeholder": _("Detailed notes about this interaction...")}),
        }


class EmailSequenceForm(BaseBootstrapForm):
    class Meta:
        model = EmailSequence
        fields = ["name", "trigger_stage", "is_active", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class EmailStepForm(BaseBootstrapForm):
    class Meta:
        model = EmailStep
        fields = ["step_number", "delay_days", "subject", "body_template"]
        widgets = {
            "body_template": forms.Textarea(attrs={"rows": 5}),
        }


class SegmentForm(BaseBootstrapForm):
    class Meta:
        model = Segment
        fields = ["name", "description", "filter_rules"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class BroadcastEmailForm(forms.Form):
    subject = forms.CharField(
        max_length=255,
        label=_("Email Subject"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Enter campaign subject...")}),
    )
    message = forms.CharField(
        label=_("HTML / Plain Message"),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 6, "placeholder": _("Write your email body here...")}),
    )
