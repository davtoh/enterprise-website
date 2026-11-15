import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestWebProgram:
    """Tests for Brython WebProgram application views."""

    def test_webprogram_index_view(self, client):
        response = client.get(reverse("webprogram:index"))
        assert response.status_code == 200
        assert "title" in response.context
        assert "brython" in response.content.decode().lower()
