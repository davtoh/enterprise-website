from import_export import resources
from .models import Company, Contact, Lead


class CompanyResource(resources.ModelResource):
    """Import/export resource for CRM Company records."""

    class Meta:
        model = Company
        import_id_fields = ("id",)
        fields = (
            "id",
            "name",
            "industry",
            "website",
            "phone",
            "address",
            "city",
            "country",
            "annual_revenue",
            "notes",
            "created_at",
        )
        export_order = fields


class ContactResource(resources.ModelResource):
    """Import/export resource for CRM Contact records."""

    class Meta:
        model = Contact
        import_id_fields = ("id",)
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "company",
            "job_title",
            "is_subscribed",
            "tags",
            "security_clearance",
            "presence_status",
            "license_plate",
            "security_tag",
            "notes",
            "created_at",
        )
        export_order = fields


class LeadResource(resources.ModelResource):
    """Import/export resource for CRM Lead records."""

    class Meta:
        model = Lead
        import_id_fields = ("id",)
        fields = (
            "id",
            "title",
            "contact",
            "company",
            "stage",
            "source",
            "value",
            "expected_close_date",
            "assigned_to",
            "notes",
            "created_at",
        )
        export_order = fields
