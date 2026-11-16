import pytest
from django.urls import reverse

from crm.models import Contact, InteractionLog, Lead, LeadSource
from todo.models import Todo


@pytest.mark.django_db
class TestHomePages:
    """Tests for all 5 public pages in the home application."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from django.core.cache import cache

        cache.clear()
        yield
        cache.clear()

    @pytest.mark.parametrize("route_name", [
        "home:index",
        "home:index_file",
        "home:about",
        "home:about_file",
        "home:services",
        "home:services_file",
        "home:products",
        "home:products_file",
        "home:contact",
        "home:contact_file",
    ])
    def test_pages_return_200(self, client, route_name):
        url = reverse(route_name)
        response = client.get(url)
        assert response.status_code == 200

    def test_home_page_context_and_content(self, client):
        response = client.get(reverse("home:index"))
        assert response.status_code == 200
        assert "Enterprise Website" in response.content.decode()

    def test_contact_form_submission_success(self, client):
        url = reverse("home:contact")
        post_data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "subject": "Inquiry about Services",
            "message": "Hello, I would like to learn more about your offerings.",
        }
        response = client.post(url, post_data, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) > 0
        assert "Jane Doe" in str(messages[0])

        contact = Contact.objects.get(email="jane@example.com")
        assert contact.first_name == "Jane"
        assert contact.last_name == "Doe"

        lead = Lead.objects.get(contact=contact)
        assert lead.source == LeadSource.WEBSITE
        assert lead.title == "Inquiry about Services"
        assert lead.notes == "Hello, I would like to learn more about your offerings."

        interaction = InteractionLog.objects.get(lead=lead, contact=contact)
        assert "Inquiry about Services" in interaction.summary

        followup = Todo.objects.get(title__icontains="Jane Doe")
        assert "jane@example.com" in followup.text
        assert "Hello, I would like to learn more about your offerings." in followup.text

    def test_contact_form_submission_updates_existing_contact(self, client):
        Contact.objects.create(first_name="Old", last_name="Name", email="repeat@example.com")
        url = reverse("home:contact")
        response = client.post(
            url,
            {
                "name": "Alice Smith",
                "email": "Repeat@Example.com",
                "subject": "",
                "message": "Second inquiry",
            },
            follow=True,
        )
        assert response.status_code == 200
        assert Contact.objects.filter(email="repeat@example.com").count() == 1
        contact = Contact.objects.get(email="repeat@example.com")
        assert contact.first_name == "Alice"
        assert contact.last_name == "Smith"
        assert Lead.objects.filter(contact=contact, source=LeadSource.WEBSITE).count() == 1
        assert Todo.objects.filter(title__icontains="Alice Smith").count() == 1

    def test_contact_form_submission_updates_mixed_case_existing_contact(self, client):
        existing = Contact.objects.create(first_name="Legacy", last_name="User", email="MixedCase@Example.com")
        url = reverse("home:contact")
        response = client.post(
            url,
            {
                "name": "Updated Person",
                "email": "mixedcase@example.com",
                "subject": "Follow-up",
                "message": "Checking case-insensitive deduplication",
            },
            follow=True,
        )
        assert response.status_code == 200
        assert Contact.objects.filter(email__iexact="mixedcase@example.com").count() == 1
        existing.refresh_from_db()
        assert existing.first_name == "Updated"
        assert existing.last_name == "Person"
        assert Lead.objects.filter(contact=existing, source=LeadSource.WEBSITE).count() == 1
        assert Todo.objects.filter(title__icontains="Updated Person").count() == 1

    def test_contact_form_submission_validation_failure(self, client):
        url = reverse("home:contact")
        # Missing required fields
        post_data = {
            "name": "",
            "email": "jane@example.com",
            "subject": "Missing name",
            "message": "",
        }
        response = client.post(url, post_data, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) > 0
        assert any(m.level_tag == "alert-danger" or "error" in m.tags for m in messages)
        assert Contact.objects.count() == 0
        assert Lead.objects.count() == 0
        assert InteractionLog.objects.count() == 0
        assert Todo.objects.count() == 0

    @pytest.mark.parametrize(
        ("route_name", "expected_slug"),
        [
            ("home:index", "home"),
            ("home:about", "about"),
            ("home:services", "services"),
            ("home:products", "products"),
            ("home:contact", "contact"),
        ],
    )
    def test_home_views_expose_seeded_cms_page_context(self, client, route_name, expected_slug):
        from cms.seed import seed_initial_cms_pages

        seed_initial_cms_pages()
        response = client.get(reverse(route_name))
        assert response.status_code == 200
        assert response.context["cms_page"] is not None
        assert response.context["cms_page"].slug == expected_slug

    def test_products_view_renders_published_erp_products(self, client):
        from decimal import Decimal
        from erp.models import Category, Product

        cat = Category.objects.create(name="Robotics")
        Product.objects.create(
            sku="PUB-R1",
            name="Autonomous Rover R1",
            category=cat,
            public_summary="Rugged indoor/outdoor telemetry rover.",
            unit_price=Decimal("1999.00"),
            is_active=True,
            is_published=True,
        )
        Product.objects.create(
            sku="PRIV-R2",
            name="Secret R2 Prototype",
            category=cat,
            is_active=True,
            is_published=False,
        )
        Product.objects.create(
            sku="INACT-R3",
            name="Retired R3",
            category=cat,
            is_active=False,
            is_published=True,
        )

        response = client.get(reverse("home:products"))
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "Autonomous Rover R1" in html
        assert "Rugged indoor/outdoor telemetry rover." in html
        assert "Secret R2 Prototype" not in html
        assert "Retired R3" not in html

    def test_contact_form_submission_links_todo_to_lead(self):
        from crm.models import Lead
        from home.services import ingest_website_contact_submission
        from todo.models import Todo

        contact, lead, _interaction, followup_todo = ingest_website_contact_submission(
            name="Grace Hopper",
            email="grace@example.com",
            subject="Compiler Inquiry",
            message="Interested in enterprise support.",
        )
        followup_todo.refresh_from_db()
        assert isinstance(lead, Lead)
        assert isinstance(followup_todo, Todo)
        assert followup_todo.content_object == lead
        assert followup_todo.object_id == lead.pk
        assert contact.email == "grace@example.com"


@pytest.mark.django_db
class TestLocationManagementResources:
    """Verify Unfold + Import/Export ModelResources for location_management."""

    def test_location_admins_use_unfold_and_import_export(self):
        from django.contrib import admin
        from import_export.admin import ImportExportModelAdmin
        from unfold.admin import ModelAdmin as UnfoldModelAdmin
        from location_management.models import Cities, Countries, Location, States

        for model in (Countries, States, Cities, Location):
            model_admin = admin.site._registry[model]
            assert isinstance(model_admin, UnfoldModelAdmin)
            assert isinstance(model_admin, ImportExportModelAdmin)

    def test_location_resources_export_and_dry_run_import(self):
        from decimal import Decimal
        from location_management.models import Cities, Countries, Location, States
        from location_management.resources import (
            CitiesResource,
            CountriesResource,
            LocationResource,
            StatesResource,
        )

        country = Countries.objects.create(name="United States", code="US")
        state = States.objects.create(country=country, name="Texas", code="TX")
        city = Cities.objects.create(
            country=country,
            state=state,
            name="Austin",
            latitude=Decimal("30.26715300"),
            longitude=Decimal("-97.74306080"),
        )
        loc = Location.objects.create(name="Austin HQ", code="AUS-HQ", city=city)

        for resource_cls, qs in (
            (CountriesResource, Countries.objects.filter(pk=country.pk)),
            (StatesResource, States.objects.filter(pk=state.pk)),
            (CitiesResource, Cities.objects.filter(pk=city.pk)),
            (LocationResource, Location.objects.filter(pk=loc.pk)),
        ):
            resource = resource_cls()
            dataset = resource.export(qs)
            assert len(dataset) == 1
            result = resource.import_data(dataset, dry_run=True)
            assert not result.has_errors()

