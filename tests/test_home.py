import pytest
from django.urls import reverse

from crm.models import Contact, InteractionLog, Lead, LeadSource
from todo.models import Todo


@pytest.mark.django_db
class TestHomePages:
    """Tests for all 5 public pages in the home application."""

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
