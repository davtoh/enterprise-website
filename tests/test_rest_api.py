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


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staffadmin",
        email="staff@example.com",
        password="StaffPassword123!",
        is_staff=True,
    )


@pytest.mark.django_db
class TestRestApi:
    """Tests for Django REST Framework API endpoints."""

    def test_api_root_endpoint(self, api_client):
        url = reverse("rest_api:api-root")
        response = api_client.get(url)
        assert response.status_code == 200
        assert "users" in response.data

    def test_users_list_requires_authentication(self, api_client, api_users):
        url = reverse("rest_api:siteuser-list")
        response = api_client.get(url)
        assert response.status_code == 403

    def test_users_list_endpoint_staff(self, api_client, api_users, staff_user):
        api_client.force_authenticate(user=staff_user)
        url = reverse("rest_api:siteuser-list")
        response = api_client.get(url)
        assert response.status_code == 200
        items = response.data.get("results", response.data)
        assert len(items) >= 3
        usernames = [u["username"] for u in items]
        assert "alice" in usernames
        assert "bob" in usernames

    def test_users_list_non_staff_self_scoped(self, api_client, api_users):
        alice, bob = api_users
        api_client.force_authenticate(user=alice)
        url = reverse("rest_api:siteuser-list")
        response = api_client.get(url)
        assert response.status_code == 200
        items = response.data.get("results", response.data)
        usernames = [u["username"] for u in items]
        assert usernames == ["alice"]
        assert "bob" not in usernames

    def test_users_detail_endpoint(self, api_client, api_users):
        alice, bob = api_users
        api_client.force_authenticate(user=alice)
        url = reverse("rest_api:siteuser-detail", kwargs={"pk": alice.pk})
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["username"] == "alice"
        assert response.data["email"] == "alice@example.com"

        other_url = reverse("rest_api:siteuser-detail", kwargs={"pk": bob.pk})
        other_response = api_client.get(other_url)
        assert other_response.status_code == 404

    def test_dynamic_fields_filtering(self, api_client, api_users, staff_user):
        # The UserSerializer supports ?val=username&val=email to dynamically trim fields
        api_client.force_authenticate(user=staff_user)
        url = reverse("rest_api:siteuser-list") + "?val=username&val=email"
        response = api_client.get(url)
        assert response.status_code == 200
        items = response.data.get("results", response.data)
        first_item = items[0]
        assert "username" in first_item
        assert "email" in first_item
        assert "phone_number" not in first_item

    def test_user_detail_not_found(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        url = reverse("rest_api:siteuser-detail", kwargs={"pk": 99999})
        response = api_client.get(url)
        assert response.status_code == 404

    def test_v1_openapi_schema_endpoint(self, api_client):
        url = reverse("schema")
        response = api_client.get(url, HTTP_ACCEPT="application/json")
        assert response.status_code == 200
        assert str(response.data.get("openapi", "")).startswith("3.")
        paths = response.data.get("paths", {})
        assert "/api/v1/users/" in paths
        assert "/api/v1/security/events/" in paths

    def test_v1_swagger_and_redoc_endpoints(self, api_client):
        docs_response = api_client.get(reverse("swagger-ui"))
        assert docs_response.status_code == 200
        assert "SwaggerUIBundle" in docs_response.content.decode("utf-8")

        redoc_response = api_client.get(reverse("redoc"))
        assert redoc_response.status_code == 200

    def test_v1_users_endpoint_via_plugin_api_urlpatterns(self, api_client, api_users, staff_user):
        anon_resp = api_client.get("/api/v1/users/")
        assert anon_resp.status_code == 403

        api_client.force_authenticate(user=staff_user)
        staff_resp = api_client.get("/api/v1/users/")
        assert staff_resp.status_code == 200
        items = staff_resp.data.get("results", staff_resp.data)
        usernames = [u["username"] for u in items]
        assert "alice" in usernames
        assert "bob" in usernames
