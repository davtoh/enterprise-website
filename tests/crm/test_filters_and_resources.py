import pytest
from django.contrib import admin
from django.urls import reverse
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from crm.filters import CompanyFilter, ContactFilter, LeadFilter
from crm.models import (
    Company,
    Contact,
    Lead,
    LeadStage,
    PresenceStatus,
    SecurityClearance,
)
from crm.resources import CompanyResource, ContactResource, LeadResource


@pytest.mark.django_db
class TestCRMFiltersAndResources:
    """Verify FilterSets, Import/Export ModelResources, and HTMX partials in CRM."""

    def test_company_filter_search(self, test_company):
        Company.objects.create(name="Beta Robotics", industry="Hardware", city="Austin")
        qs = CompanyFilter({"q": test_company.name[:4]}, queryset=Company.objects.all()).qs
        assert list(qs) == [test_company]

    def test_contact_filter_clearance_presence_and_tag(self, test_contact):
        other = Contact.objects.create(
            first_name="Bob",
            last_name="Builder",
            email="bob@example.com",
            security_clearance=SecurityClearance.CONTRACTOR,
            presence_status=PresenceStatus.ON_PREMISES,
            tags="vip,robotics",
        )
        qs = ContactFilter(
            {"clearance": "CONTRACTOR", "presence": "on_premises", "tag": "robotics"},
            queryset=Contact.objects.all(),
        ).qs
        assert list(qs) == [other]

    def test_lead_filter_stage_and_search(self, test_lead):
        other = Lead.objects.create(title="Legacy Migration", stage=LeadStage.WON)
        qs = LeadFilter({"stage": LeadStage.WON, "q": "Legacy"}, queryset=Lead.objects.all()).qs
        assert list(qs) == [other]
        assert test_lead not in qs

    def test_crm_resources_export_and_dry_run_import(self, test_company, test_contact, test_lead):
        for resource_cls, qs in (
            (CompanyResource, Company.objects.filter(pk=test_company.pk)),
            (ContactResource, Contact.objects.filter(pk=test_contact.pk)),
            (LeadResource, Lead.objects.filter(pk=test_lead.pk)),
        ):
            resource = resource_cls()
            dataset = resource.export(qs)
            assert len(dataset) == 1
            result = resource.import_data(dataset, dry_run=True)
            assert not result.has_errors()

    def test_crm_admin_uses_unfold_and_import_export(self):
        for model in (Company, Contact, Lead):
            model_admin = admin.site._registry[model]
            assert isinstance(model_admin, UnfoldModelAdmin)
            assert isinstance(model_admin, ImportExportModelAdmin)

    def test_crm_list_views_htmx_partial_rendering(
        self, client, auth_user, test_company, test_contact, test_lead
    ):
        client.force_login(auth_user)
        for url_name, query, expected_text in (
            ("crm:company_list", test_company.name, test_company.name),
            ("crm:contact_list", test_contact.email, test_contact.email),
            ("crm:lead_list", test_lead.title, test_lead.title),
        ):
            resp = client.get(
                reverse(url_name),
                {"q": query},
                headers={"HX-Request": "true"},
            )
            assert resp.status_code == 200
            html = resp.content.decode("utf-8")
            assert expected_text in html
            assert "<html" not in html.lower()
