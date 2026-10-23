import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from timezone_management.middleware import TimezoneMiddleware


@pytest.mark.django_db
class TestTimezoneManagement:
    """Tests for timezone selection view and middleware activation."""

    def test_timezone_select_page_get(self, client):
        url = reverse("set_timezone")
        response = client.get(url)
        assert response.status_code == 200
        assert "Time zone:" in response.content.decode()
        assert "America/Bogota" in response.content.decode()

    def test_set_timezone_post_saves_to_session(self, client):
        url = reverse("set_timezone")
        response = client.post(url, {"timezone": "Europe/Paris", "next": "/"}, follow=True)
        assert response.status_code == 200
        assert client.session.get("django_timezone") == "Europe/Paris"

    def test_timezone_middleware_activates_tz(self, rf):
        request = rf.get("/")
        request.session = {"django_timezone": "Asia/Tokyo"}

        middleware = TimezoneMiddleware(get_response=lambda r: None)
        middleware.process_request(request)

        current_tz = str(timezone.get_current_timezone())
        assert "Tokyo" in current_tz

    def test_timezone_middleware_deactivates_when_empty(self, rf):
        request = rf.get("/")
        request.session = {}

        middleware = TimezoneMiddleware(get_response=lambda r: None)
        middleware.process_request(request)

        # When deactivated, defaults to settings.TIME_ZONE ('America/Bogota')
        current_tz = str(timezone.get_current_timezone())
        assert "Bogota" in current_tz or "America/Bogota" in current_tz
