import pytest
from django.urls import reverse
from webprogram.views import index2


@pytest.mark.django_db
class TestWebProgram:
    """Tests for Brython WebProgram application views."""

    def test_webprogram_index_view(self, client):
        response = client.get(reverse("webprogram:index"))
        assert response.status_code == 200
        assert "title" in response.context
        assert "brython" in response.content.decode().lower()

    def test_webprogram_index2_view(self, rf):
        request = rf.get("/webprogram/test/")
        response = index2(request)
        assert response.status_code == 200
