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
