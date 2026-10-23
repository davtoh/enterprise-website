import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_users(db):
    u1 = User.objects.create_user(
        username="alice",
        email="alice@example.com",
        password="AlicePassword123!",
        first_name="Alice",
        last_name="Smith",
    )
    u2 = User.objects.create_user(
        username="bob",
        email="bob@example.com",
        password="BobPassword123!",
        first_name="Bob",
        last_name="Jones",
    )
    return [u1, u2]


@pytest.mark.django_db
class TestRestApi:
    """Tests for Django REST Framework API endpoints."""

    def test_api_root_endpoint(self, api_client):
        url = reverse("rest_api:api-root")
        response = api_client.get(url)
        assert response.status_code == 200
        assert "users" in response.data

    def test_users_list_endpoint(self, api_client, api_users):
        url = reverse("rest_api:siteuser-list")
        response = api_client.get(url)
        assert response.status_code == 200
        items = response.data.get("results", response.data)
        assert len(items) >= 2
        usernames = [u["username"] for u in items]
        assert "alice" in usernames
        assert "bob" in usernames

    def test_users_detail_endpoint(self, api_client, api_users):
        user = api_users[0]
        url = reverse("rest_api:siteuser-detail", kwargs={"pk": user.pk})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["username"] == "alice"
        assert response.data["email"] == "alice@example.com"

    def test_dynamic_fields_filtering(self, api_client, api_users):
        # The UserSerializer supports ?val=username&val=email to dynamically trim fields
        url = reverse("rest_api:siteuser-list") + "?val=username&val=email"
        response = api_client.get(url)
        assert response.status_code == 200
        items = response.data.get("results", response.data)
        first_item = items[0]
        assert "username" in first_item
        assert "email" in first_item
        assert "phone_number" not in first_item


    def test_user_detail_not_found(self, api_client):
        url = reverse("rest_api:siteuser-detail", kwargs={"pk": 99999})
        response = api_client.get(url)
        assert response.status_code == 404
