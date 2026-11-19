import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory
from wagtail.models import Locale, Page, Site

from cms.bridge import sync_wagtail_menus
from cms.models import StandardPage
from menu_management.cache import get_menu_cache_version
from menu_management.context_processors import dynamic_menu, get_menu_tree
from menu_management.models import Menu, MenuItem
from menu_management.sync import sync_plugin_menus
from plugin_registry.models import PluginState

User = get_user_model()


def _get_or_create_default_root():
    """Return the default Site's root_page on testserver."""
    site = Site.objects.filter(is_default_site=True).first()
    if site is not None:
        if site.hostname != "testserver":
            site.hostname = "testserver"
            site.save()
        return site.root_page
    root = Page.get_first_root_node() or Page.add_root(title="Root", slug="root")
    Site.objects.create(
        hostname="testserver",
        port=80,
        root_page=root,
        is_default_site=True,
        site_name="Test Enterprise Site",
    )
    return root


@pytest.fixture
def clean_cms_menu_db(db):
    cache.clear()
    MenuItem.objects.all().delete()
    Menu.objects.all().delete()
    PluginState.objects.all().delete()


@pytest.mark.django_db
class TestWagtailMenuBridge:
    """Tests for 3-level Wagtail-to-MenuItem synchronization and idempotency."""

    def test_sync_wagtail_menus_3_levels_and_idempotent(self, clean_cms_menu_db):
        root = _get_or_create_default_root()

        lvl1 = StandardPage(title="Services", slug="services-nav", show_in_menus=True)
        root.add_child(instance=lvl1)
        lvl1.save_revision().publish()

        lvl2 = StandardPage(title="Consulting", slug="consulting-nav", show_in_menus=True)
        lvl1.add_child(instance=lvl2)
        lvl2.save_revision().publish()

        lvl3 = StandardPage(title="Cloud Audit", slug="cloud-audit-nav", show_in_menus=True)
        lvl2.add_child(instance=lvl3)
        lvl3.save_revision().publish()

        lvl4 = StandardPage(title="Deep Hidden", slug="deep-hidden-nav", show_in_menus=True)
        lvl3.add_child(instance=lvl4)
        lvl4.save_revision().publish()

        hidden = StandardPage(title="Secret Page", slug="secret-nav", show_in_menus=False)
        root.add_child(instance=hidden)
        hidden.save_revision().publish()

        synced_first = sync_wagtail_menus()
        synced_second = sync_wagtail_menus()
        assert synced_first == 3
        assert synced_second == 3
        assert MenuItem.objects.filter(plugin_source="cms").count() == 3

        assert MenuItem.objects.filter(wagtail_page=lvl4).exists() is False
        assert MenuItem.objects.filter(wagtail_page=hidden).exists() is False

        tree = get_menu_tree("main_navbar", language_code="en")
        services_node = next(n for n in tree if n["title"] == "Services")
        assert services_node["level"] == 0
        assert len(services_node["children"]) == 1
        consulting_node = services_node["children"][0]
        assert consulting_node["title"] == "Consulting"
        assert consulting_node["level"] == 1
        assert len(consulting_node["children"]) == 1
        audit_node = consulting_node["children"][0]
        assert audit_node["title"] == "Cloud Audit"
        assert audit_node["level"] == 2

    def test_sync_preserves_custom_menuitem_overrides(self, clean_cms_menu_db):
        root = _get_or_create_default_root()
        page = StandardPage(title="About", slug="about-custom", show_in_menus=True)
        root.add_child(instance=page)
        page.save_revision().publish()

        sync_wagtail_menus()
        item = MenuItem.objects.get(wagtail_page=page)
        item.is_custom = True
        item.title = "Custom About Label"
        item.save()

        sync_wagtail_menus()
        item.refresh_from_db()
        assert item.title == "Custom About Label"

    def test_sync_plugin_menus_includes_wagtail_pages(self, clean_cms_menu_db):
        root = _get_or_create_default_root()
        page = StandardPage(title="Capabilities", slug="capabilities", show_in_menus=True)
        root.add_child(instance=page)
        page.save_revision().publish()

        sync_plugin_menus()
        assert MenuItem.objects.filter(wagtail_page=page).exists()


@pytest.mark.django_db
class TestLocalizedCachedNavigationAndSignals:
    """Tests for localized page titles, per-role/locale caching, and signal invalidation."""

    def test_localized_menu_title_resolution(self, clean_cms_menu_db):
        root = _get_or_create_default_root()
        en_page = StandardPage(title="Solutions", slug="solutions-i18n", show_in_menus=True)
        root.add_child(instance=en_page)
        en_page.save_revision().publish()

        es_locale, _ = Locale.objects.get_or_create(language_code="es")
        es_root = root.copy_for_translation(es_locale, copy_parents=True)
        es_root.save_revision().publish() if not es_root.live else None
        es_page = en_page.copy_for_translation(es_locale)
        es_page.title = "Soluciones"
        es_page.save_revision().publish()

        sync_wagtail_menus()

        en_tree = get_menu_tree("main_navbar", language_code="en")
        es_tree = get_menu_tree("main_navbar", language_code="es")

        assert any(node["title"] == "Solutions" for node in en_tree)
        assert any(node["title"] == "Soluciones" for node in es_tree)

    def test_menu_tree_caching_and_signal_invalidation(
        self, clean_cms_menu_db, django_assert_num_queries
    ):
        root = _get_or_create_default_root()
        page = StandardPage(title="Cached Page", slug="cached-page", show_in_menus=True)
        root.add_child(instance=page)
        page.save_revision().publish()

        # First call populates cache
        initial_tree = get_menu_tree("main_navbar", language_code="en")
        assert any(n["title"] == "Cached Page" for n in initial_tree)

        # Second call hits cache with zero DB queries
        with django_assert_num_queries(0):
            cached_tree = get_menu_tree("main_navbar", language_code="en")
        assert cached_tree == initial_tree

        version_before = get_menu_cache_version()
        page.unpublish()
        version_after = get_menu_cache_version()
        assert version_after > version_before

        refreshed_tree = get_menu_tree("main_navbar", language_code="en")
        assert not any(n["title"] == "Cached Page" for n in refreshed_tree)

    def test_dynamic_menu_extracts_active_section_sidebar(self, clean_cms_menu_db):
        root = _get_or_create_default_root()
        parent_page = StandardPage(title="Platform", slug="platform", show_in_menus=True)
        root.add_child(instance=parent_page)
        parent_page.save_revision().publish()

        child_page = StandardPage(title="Architecture", slug="architecture", show_in_menus=True)
        parent_page.add_child(instance=child_page)
        child_page.save_revision().publish()

        sync_wagtail_menus()

        rf = RequestFactory()
        request = rf.get(child_page.url)
        request.LANGUAGE_CODE = "en"
        context = dynamic_menu(request)

        assert context["section_sidebar"] is not None
        assert context["section_sidebar"]["title"] == "Platform"
        assert context["section_sidebar"]["items"][0]["title"] == "Architecture"
