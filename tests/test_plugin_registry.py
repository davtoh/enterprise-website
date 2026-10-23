import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory

from menu_management.context_processors import dynamic_menu
from menu_management.models import Menu, MenuItem
from menu_management.sync import sync_plugin_menus
from plugin_registry import AppPlugin, MenuItemDefinition, registry

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


