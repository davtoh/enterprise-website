from datetime import date
import pytest
from django.conf import settings
from django.urls import reverse
from wagtail.models import Locale, Page, Site

from cms.models import BlogCategory, BlogIndexPage, BlogPage, StandardPage
from plugin_registry import PluginZone, registry


def _get_or_create_wagtail_root():
    """Return the default Site's root_page and ensure hostname matches testserver."""
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


@pytest.mark.django_db
class TestWagtailCMSSetup:
    """Tests for Wagtail core routing, plugin registration, and i18n configuration."""

    def test_cms_admin_login_resolves(self, client):
        url = reverse("wagtailadmin_login")
        assert url == "/cms/login/"
        response = client.get(url)
        assert response.status_code == 200

    def test_cms_plugin_registered_as_system(self):
        plugin = registry.get_plugin("cms")
        assert plugin is not None
        assert plugin.is_system is True
        assert plugin.get_zone() == PluginZone.PUBLIC

    def test_wagtail_i18n_matches_settings_languages(self):
        assert settings.WAGTAIL_I18N_ENABLED is True
        assert list(settings.WAGTAIL_CONTENT_LANGUAGES) == list(settings.LANGUAGES)
        expected_codes = {"en", "es", "pt", "fr", "it", "ja"}
        assert {code for code, _ in settings.WAGTAIL_CONTENT_LANGUAGES} == expected_codes


@pytest.mark.django_db
class TestCMSPagesAndBlocks:
    """Tests for StandardPage, BlogIndexPage, BlogPage, StreamField blocks, and multi-theme rendering."""

    @pytest.mark.parametrize("theme_name", ["bootstrap5", "tailwind", "minimal"])
    def test_standard_page_renders_streamfield_across_themes(self, client, theme_name):
        root = _get_or_create_wagtail_root()
        page = StandardPage(
            title=f"Solutions ({theme_name})",
            slug=f"solutions-{theme_name}",
            intro="Enterprise modular platform",
            body=[
                (
                    "hero",
                    {
                        "heading": "Build Faster",
                        "subheading": "Composable enterprise blocks",
                        "cta_text": "Contact Sales",
                        "cta_url": "/contact/",
                    },
                ),
                (
                    "richtext",
                    {
                        "heading": "Overview",
                        "body": "<p>Rich editorial content.</p>",
                    },
                ),
                (
                    "features",
                    {
                        "heading": "Capabilities",
                        "features": [
                            {
                                "icon": "fa-rocket",
                                "title": "High Speed",
                                "description": "Cached navigation and clean templates.",
                            }
                        ],
                    },
                ),
                (
                    "cta",
                    {
                        "heading": "Ready to start?",
                        "body": "Talk to our team today.",
                        "button_text": "Get Started",
                        "button_url": "/contact/",
                    },
                ),
            ],
        )
        root.add_child(instance=page)
        page.save_revision().publish()

        client.get(f"/theme/switch/{theme_name}/")
        response = client.get(page.url)
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "Build Faster" in html
        assert "Rich editorial content." in html
        assert "fa fa-rocket" in html
        assert "Ready to start?" in html
        assert "!important" not in html

    def test_blog_index_and_blog_page_with_category_filter(self, client):
        root = _get_or_create_wagtail_root()
        en_locale = Locale.get_default()
        cat_eng = BlogCategory.objects.create(name="Engineering", slug="engineering", locale=en_locale)
        cat_news = BlogCategory.objects.create(name="News", slug="news", locale=en_locale)

        blog_index = BlogIndexPage(title="Company Blog", slug="blog", intro="<p>Latest updates</p>")
        root.add_child(instance=blog_index)
        blog_index.save_revision().publish()

        post_one = BlogPage(
            title="Scaling Django & Wagtail",
            slug="scaling-django-wagtail",
            date=date(2026, 11, 1),
            intro="Architecture deep dive",
            body=[("richtext", {"heading": "Details", "body": "<p>StreamField post body.</p>"})],
        )
        blog_index.add_child(instance=post_one)
        post_one.categories.add(cat_eng)
        post_one.save_revision().publish()

        post_two = BlogPage(
            title="Q4 Release Announcement",
            slug="q4-release",
            date=date(2026, 11, 2),
            intro="Product milestone",
        )
        blog_index.add_child(instance=post_two)
        post_two.categories.add(cat_news)
        post_two.save_revision().publish()

        index_resp = client.get(blog_index.url)
        assert index_resp.status_code == 200
        index_html = index_resp.content.decode("utf-8")
        assert "Scaling Django &amp; Wagtail" in index_html or "Scaling Django & Wagtail" in index_html
        assert "Q4 Release Announcement" in index_html

        filtered_resp = client.get(f"{blog_index.url}?category=engineering")
        assert filtered_resp.status_code == 200
        filtered_html = filtered_resp.content.decode("utf-8")
        assert "Scaling Django" in filtered_html
        assert "Q4 Release Announcement" not in filtered_html

        post_resp = client.get(post_one.url)
        assert post_resp.status_code == 200
        assert "StreamField post body." in post_resp.content.decode("utf-8")

    def test_wagtail_localize_page_and_category_translation(self):
        root = _get_or_create_wagtail_root()
        es_locale, _ = Locale.objects.get_or_create(language_code="es")

        page = StandardPage(title="About Platform", slug="about-platform", intro="English intro")
        root.add_child(instance=page)
        page.save_revision().publish()

        es_page = page.copy_for_translation(es_locale, copy_parents=True)
        es_page.title = "Sobre la Plataforma"
        es_page.intro = "Introducción en español"
        es_page.save_revision().publish()

        assert es_page.locale.language_code == "es"
        assert es_page.translation_key == page.translation_key

        cat_en = BlogCategory.objects.create(name="Cloud", slug="cloud", locale=Locale.get_default())
        cat_es = cat_en.copy_for_translation(es_locale)
        cat_es.name = "Nube"
        cat_es.save()
        assert cat_es.translation_key == cat_en.translation_key
        assert cat_es.locale == es_locale


@pytest.mark.django_db
class TestCMSSeedingAndNavigation:
    """Tests for idempotent CMS seeding, 3-level headers, and contextual section sidebar."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from django.core.cache import cache

        cache.clear()
        yield
        cache.clear()

    def test_seed_initial_cms_pages_idempotent(self):
        from django.core.management import call_command

        from cms.seed import seed_initial_cms_pages

        _get_or_create_wagtail_root()
        first = seed_initial_cms_pages()
        assert first["created"] == 7
        assert first["existing"] == 0

        second = seed_initial_cms_pages()
        assert second["created"] == 0
        assert second["existing"] == 7

        call_command("seed_cms_pages")
        assert StandardPage.objects.filter(slug="home").exists()
        assert BlogIndexPage.objects.filter(slug="blog").exists()
        assert BlogPage.objects.filter(slug="welcome-to-enterprise-cms").exists()

    @pytest.mark.parametrize("theme_name", ["bootstrap5", "tailwind", "minimal"])
    def test_standard_page_renders_3rd_level_section_sidebar_across_themes(self, client, theme_name):
        from pathlib import Path

        from cms.bridge import sync_wagtail_menus

        root = _get_or_create_wagtail_root()
        section = StandardPage(title="Company", slug="company", show_in_menus=True)
        root.add_child(instance=section)
        section.save_revision().publish()

        dept = StandardPage(title="Engineering", slug="engineering", show_in_menus=True)
        section.add_child(instance=dept)
        dept.save_revision().publish()

        team = StandardPage(title="Platform Team", slug="platform-team", show_in_menus=True)
        dept.add_child(instance=team)
        team.save_revision().publish()

        sync_wagtail_menus()

        response = client.get(f"{team.url}?theme={theme_name}")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "cms-section-sidebar" in html
        assert "Engineering" in html
        assert "Platform Team" in html

        sidebar_src = Path(settings.BASE_DIR, "templates/partials/section_sidebar.html").read_text(encoding="utf-8")
        assert "!important" not in sidebar_src
        assert 'style="' not in sidebar_src

    @pytest.mark.parametrize("theme_name", ["bootstrap5", "tailwind", "minimal"])
    def test_headers_render_clickable_parent_and_2_level_dropdown_across_themes(self, client, theme_name):
        from pathlib import Path

        from menu_management.cache import invalidate_menu_cache
        from menu_management.models import Menu, MenuItem

        menu, _ = Menu.objects.get_or_create(slug="main_navbar", defaults={"title": "Main Navbar"})
        parent = MenuItem.objects.create(menu=menu, title="Solutions", url_path="/services/", order=1)
        child = MenuItem.objects.create(menu=menu, parent=parent, title="Cloud", url_path="/products/", order=1)
        MenuItem.objects.create(menu=menu, parent=child, title="Kubernetes", url_path="/about/", order=1)
        invalidate_menu_cache()

        response = client.get(f"/?theme={theme_name}")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "Solutions" in html
        assert 'href="/services/"' in html
        assert "Toggle submenu" in html
        assert "Cloud" in html
        assert "Kubernetes" in html

        header_src = Path(settings.BASE_DIR, f"templates/themes/{theme_name}/partials/header.html").read_text(encoding="utf-8")
        assert "!important" not in header_src
        assert 'style="' not in header_src


@pytest.mark.django_db
class TestComposablePluginStreamBlocks:
    """Tests for AppPlugin v2 StreamField block registration and multi-theme rendering."""

    def test_registry_get_active_stream_blocks_respects_enabled_state(self):
        from django.core.cache import cache
        from plugin_registry.models import PluginState

        active_names = [name for name, _ in registry.get_active_stream_blocks()]
        assert "video_gallery" in active_names
        assert "poll" in active_names

        PluginState.objects.update_or_create(slug="video_gallery", defaults={"is_enabled": False})
        cache.clear()
        try:
            filtered_names = [name for name, _ in registry.get_active_stream_blocks()]
            assert "video_gallery" not in filtered_names
            assert "poll" in filtered_names
        finally:
            PluginState.objects.filter(slug="video_gallery").delete()
            cache.clear()

    @pytest.mark.parametrize("theme_name", ["bootstrap5", "tailwind", "minimal"])
    def test_standard_page_renders_video_gallery_and_poll_blocks_across_themes(self, client, theme_name):
        from pathlib import Path
        from django.utils import timezone
        from polls.models import Choice, Question
        from video_gallery.models import VideoGallery, VideoItem

        gallery = VideoGallery.objects.create(
            name="CMS Feature Demos",
            slug=f"cms-feature-demos-{theme_name}",
            is_active=True,
            is_public=True,
            requires_staff=False,
        )
        VideoItem.objects.create(
            gallery=gallery,
            title="Public Demo Reel",
            embed_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            is_public=True,
            requires_staff=False,
        )
        VideoItem.objects.create(
            gallery=gallery,
            title="Hidden Staff Clip",
            embed_url="https://www.youtube.com/watch?v=9bZkp7q19f0",
            is_public=False,
            requires_staff=True,
        )

        question = Question.objects.create(
            question_text="Which deployment mode do you prefer?",
            pub_date=timezone.now(),
            opened=True,
        )
        Choice.objects.create(question=question, choice_text="Kubernetes", votes=3)
        Choice.objects.create(question=question, choice_text="Docker Compose", votes=2)

        root = _get_or_create_wagtail_root()
        page = StandardPage(
            title=f"Showcase {theme_name}",
            slug=f"showcase-{theme_name}",
            intro="Cross-app composable blocks",
            body=[
                (
                    "video_gallery",
                    {
                        "heading": "Featured Videos",
                        "gallery_slug": gallery.slug,
                        "max_items": 3,
                    },
                ),
                (
                    "poll",
                    {
                        "heading": "Community Poll",
                        "question_id": question.id,
                    },
                ),
            ],
        )
        root.add_child(instance=page)
        page.save_revision().publish()

        response = client.get(f"{page.url}?theme={theme_name}")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "Featured Videos" in html
        assert "Public Demo Reel" in html
        assert "Hidden Staff Clip" not in html
        assert "Community Poll" in html
        assert "Which deployment mode do you prefer?" in html
        assert "Kubernetes" in html
        assert f"/polls/{question.id}/vote/" in html

        for tpl_name in ("video_gallery_embed_block.html", "poll_embed_block.html"):
            tpl_src = Path(settings.BASE_DIR, "cms/templates/cms/blocks", tpl_name).read_text(encoding="utf-8")
            assert "!important" not in tpl_src
            assert 'style="' not in tpl_src

    @pytest.mark.parametrize("theme_name", ["bootstrap5", "tailwind", "minimal"])
    def test_standard_page_renders_product_showcase_block_across_themes(self, client, theme_name):
        from decimal import Decimal
        from django.conf import settings
        from pathlib import Path
        from cms.models import StandardPage
        from erp.models import Category, Product
        from plugin_registry.registry import registry

        block_names = [name for name, _ in registry.get_active_stream_blocks()]
        assert "product_showcase" in block_names

        cat = Category.objects.create(name=f"Automation-{theme_name}")
        Product.objects.create(
            sku=f"SHOW-{theme_name}-1",
            name=f"Edge Controller {theme_name}",
            category=cat,
            public_summary="Real-time industrial edge controller.",
            unit_price=Decimal("750.00"),
            is_active=True,
            is_published=True,
        )
        Product.objects.create(
            sku=f"HIDE-{theme_name}-2",
            name=f"Hidden Draft Unit {theme_name}",
            category=cat,
            is_active=True,
            is_published=False,
        )

        root = _get_or_create_wagtail_root()
        page = StandardPage(
            title=f"Catalog {theme_name}",
            slug=f"catalog-{theme_name}",
            intro="ERP Product Showcase",
            body=[
                (
                    "product_showcase",
                    {
                        "heading": "Industrial Catalog",
                        "category_slug": cat.slug,
                        "max_items": 4,
                        "show_prices": True,
                    },
                ),
            ],
        )
        root.add_child(instance=page)
        page.save_revision().publish()

        response = client.get(f"{page.url}?theme={theme_name}")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "Industrial Catalog" in html
        assert f"Edge Controller {theme_name}" in html
        assert "Real-time industrial edge controller." in html
        assert "750.00" in html
        assert f"Hidden Draft Unit {theme_name}" not in html

        tpl_src = Path(settings.BASE_DIR, "cms/templates/cms/blocks/product_showcase_block.html").read_text(
            encoding="utf-8"
        )
        assert "!important" not in tpl_src
        assert 'style="' not in tpl_src
