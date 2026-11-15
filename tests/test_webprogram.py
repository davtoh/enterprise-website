import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from menu_management.context_processors import get_menu_tree
from menu_management.sync import sync_plugin_menus
from plugin_registry import registry
from plugin_registry.base import PluginZone

User = get_user_model()


@pytest.mark.django_db
class TestWebProgram:
    """Tests for Brython WebProgram application views and Labs zone gating."""

    @override_settings(ENABLE_LABS_PLUGINS=True)
    def test_webprogram_index_view(self, client):
        response = client.get(reverse("webprogram:index"))
        assert response.status_code == 200
        assert "title" in response.context
        assert "brython" in response.content.decode().lower()

    @override_settings(ENABLE_LABS_PLUGINS=False)
    def test_webprogram_returns_404_when_labs_disabled(self, client):
        plugin_cls = registry.get_plugin("webprogram")
        assert plugin_cls is not None
        assert plugin_cls.get_zone() == PluginZone.LABS
        assert registry.is_plugin_enabled("webprogram") is False

        response = client.get(reverse("webprogram:index"))
        assert response.status_code == 404

    def test_webprogram_menu_hidden_when_labs_disabled(self):
        sync_plugin_menus()
        user = User(username="labs_visitor")

        with override_settings(ENABLE_LABS_PLUGINS=False):
            nav = get_menu_tree("main_navbar", user=user)
            apps_node = next(item for item in nav if item["title"] == "Apps")
            child_titles = [child["title"] for child in apps_node["children"]]
            assert "Brython WebProgram" not in child_titles

        with override_settings(ENABLE_LABS_PLUGINS=True):
            nav = get_menu_tree("main_navbar", user=user)
            apps_node = next(item for item in nav if item["title"] == "Apps")
            child_titles = [child["title"] for child in apps_node["children"]]
            assert "Brython WebProgram" in child_titles
