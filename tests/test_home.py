import pytest
from django.urls import reverse


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
