from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from menu_management.context_processors import dynamic_menu, get_menu_tree
from menu_management.models import Menu, MenuItem
from menu_management.sync import sync_plugin_menus
from plugin_registry import AppPlugin, MenuItemDefinition, PluginZone, registry
from plugin_registry.middleware import PluginGatingMiddleware
from plugin_registry.models import PLUGIN_STATE_CACHE_KEY, PluginState

User = get_user_model()


@pytest.fixture
def clean_menu_db(db):
    MenuItem.objects.all().delete()
    Menu.objects.all().delete()


@pytest.mark.django_db
class TestPluginRegistryAndMenus:
    """Tests for the plugin registry and dynamic menu management system."""

    def test_registry_autodiscover(self):
        registry.autodiscover()
        plugins = registry.get_all_plugins()

        assert "home" in plugins
        assert "todo" in plugins
        assert "polls" in plugins
        assert "webprogram" in plugins
        assert "rest_api" in plugins

    def test_get_plugin_by_name(self):
        todo_plugin = registry.get_plugin("todo")
        assert todo_plugin is not None
        assert todo_plugin.name == "todo"
        assert len(todo_plugin.get_menu_items()) > 0

    def test_sync_plugin_menus_creates_hierarchy(self, clean_menu_db):
        sync_plugin_menus()

        menu = Menu.objects.get(slug="main_navbar")
        assert menu.is_active is True

        # Check Apps parent dropdown
        apps_parent = MenuItem.objects.get(menu=menu, title="Apps")
        assert apps_parent.url_path == "#"

        # Check children under Apps
        children = list(apps_parent.children.all().values_list("title", flat=True))
        assert "Todo List" in children
        assert "Polls" in children
        assert "Brython WebProgram" in children
        assert "REST API" in children
        assert "Site Admin" in children

    def test_sync_plugin_menus_is_idempotent(self, clean_menu_db):
        sync_plugin_menus()
        initial_count = MenuItem.objects.count()

        # Run sync again; count should remain unchanged
        sync_plugin_menus()
        assert MenuItem.objects.count() == initial_count

    def test_menu_item_get_url_resolution(self, clean_menu_db):
        sync_plugin_menus()
        menu = Menu.objects.get(slug="main_navbar")
        todo_item = MenuItem.objects.get(menu=menu, url_name="todo:index")

        assert todo_item.get_resolved_url() == "/todo/"

    def test_menu_item_visibility_permissions(self, clean_menu_db):
        sync_plugin_menus()
        menu = Menu.objects.get(slug="main_navbar")
        admin_item = MenuItem.objects.get(menu=menu, url_name="admin:index")

        anon_user = None
        regular_user = User(username="regular", is_staff=False)
        staff_user = User(username="staff", is_staff=True)

        assert admin_item.is_accessible_by(anon_user) is False
        assert admin_item.is_accessible_by(regular_user) is False
        assert admin_item.is_accessible_by(staff_user) is True

    def test_sync_menus_management_command(self, clean_menu_db):
        call_command("sync_menus")
        assert Menu.objects.filter(slug="main_navbar").exists()
        assert MenuItem.objects.count() > 0

    def test_dynamic_menu_context_processor(self, rf, clean_menu_db):
        sync_plugin_menus()
        request = rf.get("/")
        request.user = User(username="test_visitor")

        context = dynamic_menu(request)
        assert "main_navigation" in context
        nav = context["main_navigation"]
        assert len(nav) > 0
        root_titles = [item["title"] for item in nav]
        assert "Home" in root_titles
        assert "About Us" in root_titles
        assert "Apps" in root_titles


@pytest.mark.django_db
class TestAppPluginV2AndGating:
    """Tests for AppPlugin v2 contract, entry points, PluginState, and runtime gating."""

    @pytest.fixture(autouse=True)
    def clear_plugin_cache(self):
        cache.delete(PLUGIN_STATE_CACHE_KEY)
        yield
        cache.delete(PLUGIN_STATE_CACHE_KEY)

    def test_app_plugin_v2_defaults_and_getters(self):
        class CustomV2Plugin(AppPlugin):
            name = "custom_v2_test"
            zone = "staff"
            requires_staff = True
            requires_auth = True
            is_system = False
            stream_blocks = [("hero", "HeroBlock")]
            api_urlpatterns = ["api/v2/custom/"]
            dashboard_widgets = [{"id": "kpi_1", "title": "KPI"}]

        assert CustomV2Plugin.get_zone() is PluginZone.STAFF
        assert CustomV2Plugin.requires_staff is True
        assert CustomV2Plugin.requires_auth is True
        assert CustomV2Plugin.is_system is False
        assert CustomV2Plugin.get_stream_blocks() == [("hero", "HeroBlock")]
        assert CustomV2Plugin.get_api_urlpatterns() == ["api/v2/custom/"]
        assert CustomV2Plugin.get_dashboard_widgets() == [{"id": "kpi_1", "title": "KPI"}]
        assert AppPlugin.get_zone() is PluginZone.PUBLIC

    def test_entry_points_discovery_in_autodiscover(self):
        class ExternalEntryPlugin(AppPlugin):
            name = "external_ep_plugin"
            verbose_name = "External Entry Point Plugin"
            url_prefix = "ext_ep"

        fake_ep = MagicMock()
        fake_ep.name = "external_ep_plugin"
        fake_ep.value = "ext_pkg.plugin:ExternalEntryPlugin"
        fake_ep.load.return_value = ExternalEntryPlugin

        original_discovered = registry._discovered
        registry._discovered = False
        try:
            with patch("plugin_registry.registry.metadata.entry_points", return_value=[fake_ep]) as mock_eps:
                registry.autodiscover()
                mock_eps.assert_called_with(group="enterprise_website.plugins")
            assert registry.get_plugin("external_ep_plugin") is ExternalEntryPlugin
        finally:
            registry._plugins.pop("external_ep_plugin", None)
            registry._discovered = original_discovered

    def test_plugin_state_persistence_and_cache_invalidation(self):
        assert registry.is_plugin_enabled("todo") is True

        state = PluginState.objects.create(
            slug="todo",
            is_enabled=False,
            config_json={"max_items": 50},
        )
        assert state.config_json == {"max_items": 50}
        assert registry.is_plugin_enabled("todo") is False
        assert "todo" not in registry.get_enabled_plugins()

        state.is_enabled = True
        state.save()
        assert registry.is_plugin_enabled("todo") is True
        assert "todo" in registry.get_enabled_plugins()

        state.is_enabled = False
        state.save()
        assert registry.is_plugin_enabled("todo") is False
        state.delete()
        assert registry.is_plugin_enabled("todo") is True

    def test_registry_accessors_filter_disabled_plugins(self):
        class RichPlugin(AppPlugin):
            name = "rich_filter_test"
            tasks = ["rich.tasks.sync"]
            plugin_templates = {"bootstrap5": "rich/bs5/"}
            stream_blocks = [("rich_block", object())]
            api_urlpatterns = ["api/rich/"]

        registry.register(RichPlugin)
        try:
            assert "rich_filter_test" in registry.get_all_tasks()
            assert "rich_filter_test" in registry.get_all_plugin_templates()
            assert "rich_filter_test" in registry.get_all_stream_blocks()
            assert "rich_filter_test" in registry.get_all_api_urlpatterns()

            PluginState.objects.create(slug="rich_filter_test", is_enabled=False)

            assert "rich_filter_test" not in registry.get_all_tasks()
            assert "rich_filter_test" not in registry.get_all_plugin_templates()
            assert "rich_filter_test" not in registry.get_all_stream_blocks()
            assert "rich_filter_test" not in registry.get_all_api_urlpatterns()
        finally:
            registry._plugins.pop("rich_filter_test", None)

    def test_system_plugin_cannot_be_disabled(self):
        class CoreSystemPlugin(AppPlugin):
            name = "core_sys_test"
            is_system = True
            url_prefix = "core_sys"

        registry.register(CoreSystemPlugin)
        try:
            PluginState.objects.create(slug="core_sys_test", is_enabled=False)
            assert registry.is_plugin_enabled("core_sys_test") is True
        finally:
            registry._plugins.pop("core_sys_test", None)

    def test_plugin_gating_middleware_returns_404_when_disabled(self, rf):
        middleware = PluginGatingMiddleware(lambda req: HttpResponse("ok"))

        enabled_req = rf.get("/crm/")
        assert middleware(enabled_req).status_code == 200

        PluginState.objects.create(slug="crm", is_enabled=False)

        disabled_req = rf.get("/crm/contacts/")
        with pytest.raises(Http404):
            middleware(disabled_req)

        lang_prefixed_req = rf.get("/en/crm/contacts/")
        lang_prefixed_req.LANGUAGE_CODE = "en"
        with pytest.raises(Http404):
            middleware(lang_prefixed_req)

    def test_menu_tree_hides_disabled_plugin_items(self, clean_menu_db):
        sync_plugin_menus()
        user = User(username="menu_visitor")

        PluginState.objects.create(slug="todo", is_enabled=False)
        nav = get_menu_tree("main_navbar", user=user)
        apps_node = next(item for item in nav if item["title"] == "Apps")
        child_titles = [child["title"] for child in apps_node["children"]]
        assert "Todo List" not in child_titles
        assert "Polls" in child_titles


@pytest.mark.django_db
class TestZoneSeparationAndPropagation:
    """Milestone 2 tests for Staff/Labs/System plugin zones and menu propagation."""

    def test_staff_zone_plugins_propagate_requires_staff_to_menus(self, clean_menu_db):
        from plugin_registry.base import PluginZone

        registry.autodiscover()
        for slug in ("crm", "erp", "intelligent_tracker_hub", "task_runner"):
            plugin_cls = registry.get_plugin(slug)
            assert plugin_cls is not None
            assert plugin_cls.get_zone() == PluginZone.STAFF
            assert plugin_cls.requires_staff is True
            assert plugin_cls.requires_auth is True

        sync_plugin_menus()
        regular_user = User.objects.create_user(username="regular_user", password="pw", is_staff=False)
        staff_user = User.objects.create_user(username="staff_user", password="pw", is_staff=True)

        regular_apps = next(
            item for item in get_menu_tree("main_navbar", user=regular_user) if item["title"] == "Apps"
        )
        regular_titles = [child["title"] for child in regular_apps["children"]]
        for staff_label in ("CRM", "ERP", "Security Hub", "Background Tasks"):
            assert staff_label not in regular_titles

        staff_apps = next(
            item for item in get_menu_tree("main_navbar", user=staff_user) if item["title"] == "Apps"
        )
        staff_titles = [child["title"] for child in staff_apps["children"]]
        for staff_label in ("CRM", "ERP", "Security Hub", "Background Tasks"):
            assert staff_label in staff_titles

    def test_sync_plugin_menus_propagates_plugin_level_defaults(self, clean_menu_db):
        class StaffDefaultPlugin(AppPlugin):
            name = "staff_default_test"
            requires_auth = True
            requires_staff = True
            menu_items = [
                MenuItemDefinition(
                    label="Staff Default Item",
                    url_path="/staff-default/",
                    parent_slug="Apps",
                )
            ]

        registry.register(StaffDefaultPlugin)
        try:
            sync_plugin_menus()
            item = MenuItem.objects.get(plugin_source="staff_default_test")
            assert item.requires_auth is True
            assert item.requires_staff is True
        finally:
            registry._plugins.pop("staff_default_test", None)

    def test_core_plugins_have_is_system_protection(self):
        registry.autodiscover()
        for slug in ("home", "theme_management", "language_management"):
            plugin_cls = registry.get_plugin(slug)
            assert plugin_cls is not None
            assert plugin_cls.is_system is True
            PluginState.objects.create(slug=slug, is_enabled=False)
            assert registry.is_plugin_enabled(slug) is True


@pytest.mark.django_db
class TestUnfoldAdminAndMarketplace:
    """Milestone 3 tests for django-unfold Admin & Module Marketplace."""

    def test_unfold_admin_renders_for_staff(self, client):
        staff = User.objects.create_user(
            username="unfold_staff", password="pw", is_staff=True, is_superuser=True
        )
        client.force_login(staff)
        response = client.get("/admin/")
        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert "Module Marketplace" in body
        assert "Enterprise Workspace" in body

    def test_marketplace_requires_staff_access(self, client):
        resp_anon = client.get("/admin/marketplace/")
        assert resp_anon.status_code == 302
        assert "/admin/login/" in resp_anon.url

        regular = User.objects.create_user(username="non_staff", password="pw", is_staff=False)
        client.force_login(regular)
        resp_reg = client.get("/admin/marketplace/")
        assert resp_reg.status_code == 302
        assert "/admin/login/" in resp_reg.url

    def test_marketplace_get_and_zone_filtering(self, client):
        staff = User.objects.create_user(username="mkt_staff", password="pw", is_staff=True)
        client.force_login(staff)

        resp = client.get("/admin/marketplace/")
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert "Module Marketplace" in body
        assert "todo" in body

        resp_staff_zone = client.get("/admin/marketplace/?zone=staff")
        assert resp_staff_zone.status_code == 200
        staff_body = resp_staff_zone.content.decode("utf-8")
        assert "crm" in staff_body
        assert "todo" not in staff_body

    def test_marketplace_post_toggles_plugin_state(self, client):
        staff = User.objects.create_user(username="toggle_staff", password="pw", is_staff=True)
        client.force_login(staff)

        resp_disable = client.post(
            "/admin/marketplace/",
            {"slug": "todo", "action": "disable"},
            follow=True,
        )
        assert resp_disable.status_code == 200
        assert PluginState.objects.get(slug="todo").is_enabled is False
        assert registry.is_plugin_enabled("todo") is False

        resp_enable = client.post(
            "/admin/marketplace/",
            {"slug": "todo", "action": "enable"},
            follow=True,
        )
        assert resp_enable.status_code == 200
        assert PluginState.objects.get(slug="todo").is_enabled is True
        assert registry.is_plugin_enabled("todo") is True

    def test_marketplace_blocks_disabling_system_plugin(self, client):
        staff = User.objects.create_user(username="sys_staff", password="pw", is_staff=True)
        client.force_login(staff)

        resp = client.post(
            "/admin/marketplace/",
            {"slug": "home", "action": "disable"},
            follow=True,
        )
        assert resp.status_code == 200
        assert "cannot be disabled" in resp.content.decode("utf-8")
        assert registry.is_plugin_enabled("home") is True




