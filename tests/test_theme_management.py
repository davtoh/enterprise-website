import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import reverse

from django.contrib.auth import get_user_model
from theme_management.context_processors import theme_context
from theme_management.middleware import (
    ThemeMiddleware,
    get_current_theme,
    set_current_theme,
    clear_current_theme,
)
from plugin_registry import registry
from todo.models import Todo

User = get_user_model()


@pytest.fixture(autouse=True)
def clean_theme():
    clear_current_theme()
    yield
    clear_current_theme()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="theme_admin",
        email="admin@theme.com",
        password="TestPassword123!",
        is_staff=True,
    )


@pytest.mark.django_db
class TestThemeManagement:

    def test_default_theme_settings(self):
        assert hasattr(settings, 'SITE_THEME')
        assert hasattr(settings, 'AVAILABLE_THEMES')
        assert 'bootstrap5' in settings.AVAILABLE_THEMES
        assert 'tailwind' in settings.AVAILABLE_THEMES
        assert 'minimal' in settings.AVAILABLE_THEMES

    def test_get_current_theme_fallback(self):
        clear_current_theme()
        theme = get_current_theme()
        assert theme in settings.AVAILABLE_THEMES

    def test_set_and_get_current_theme(self):
        set_current_theme('tailwind')
        assert get_current_theme() == 'tailwind'

        set_current_theme('minimal')
        assert get_current_theme() == 'minimal'

        set_current_theme('bootstrap5')
        assert get_current_theme() == 'bootstrap5'

    def test_theme_middleware_query_param(self, rf: RequestFactory):
        middleware = ThemeMiddleware(get_response=lambda r: None)
        request = rf.get('/?theme=tailwind')
        request.session = {}
        middleware.process_request(request)

        assert request.site_theme == 'tailwind'
        assert request.session.get('site_theme') == 'tailwind'
        assert request._theme_set_cookie is True

    def test_theme_middleware_invalid_theme(self, rf: RequestFactory):
        middleware = ThemeMiddleware(get_response=lambda r: None)
        request = rf.get('/?theme=nonexistent_theme')
        request.session = {}
        middleware.process_request(request)

        assert request.site_theme == 'bootstrap5'

    def test_theme_middleware_session_preference(self, rf: RequestFactory):
        middleware = ThemeMiddleware(get_response=lambda r: None)
        request = rf.get('/')
        request.session = {'site_theme': 'minimal'}
        middleware.process_request(request)

        assert request.site_theme == 'minimal'

    def test_theme_context_processor(self, rf: RequestFactory):
        request = rf.get('/')
        request.site_theme = 'tailwind'
        ctx = theme_context(request)

        assert ctx['site_theme'] == 'tailwind'
        assert 'available_themes' in ctx
        assert len(ctx['theme_choices']) == 3
        tailwind_choice = next(c for c in ctx['theme_choices'] if c['name'] == 'tailwind')
        assert tailwind_choice['is_active'] is True

    def test_set_theme_view_get(self, client):
        url = reverse('theme_management:set_theme', kwargs={'theme_name': 'tailwind'})
        response = client.get(f"{url}?next=/about/")

        assert response.status_code == 302
        assert response.url == '/about/'
        assert client.session.get('site_theme') == 'tailwind'
        assert response.cookies['site_theme'].value == 'tailwind'

    def test_set_theme_view_post(self, client):
        url = reverse('theme_management:set_theme_form')
        response = client.post(url, {'theme': 'minimal', 'next': '/services/'})

        assert response.status_code == 302
        assert response.url == '/services/'
        assert client.session.get('site_theme') == 'minimal'
        assert response.cookies['site_theme'].value == 'minimal'

    def test_set_theme_view_invalid_safe_redirect(self, client):
        url = reverse('theme_management:set_theme', kwargs={'theme_name': 'bootstrap5'})
        response = client.get(f"{url}?next=https://malicious-site.com/phish")

        assert response.status_code == 302
        # Untrusted external redirects must fall back safely to '/'
        assert response.url == '/'

    def test_template_loader_bootstrap5_resolution(self):
        set_current_theme('bootstrap5')
        rendered = render_to_string('base.html', {'title': 'BS5 Test'})
        assert 'bootstrap' in rendered.lower()
        assert 'cdn.jsdelivr.net/npm/bootstrap@5.3.3' in rendered

    def test_template_loader_tailwind_resolution(self):
        set_current_theme('tailwind')
        rendered = render_to_string('base.html', {'title': 'Tailwind Test'})
        assert 'cdn.tailwindcss.com' in rendered

    def test_template_loader_minimal_resolution(self):
        set_current_theme('minimal')
        rendered = render_to_string('base.html', {'title': 'Minimal Test'})
        assert '--color-primary' in rendered

    def test_all_core_routes_across_all_themes(self, client, staff_user):
        client.force_login(staff_user)
        routes = ['/', '/about/', '/services/', '/products/', '/contact/', '/todo/', '/polls/', '/tasks/']
        for theme in ['bootstrap5', 'tailwind', 'minimal']:
            for route in routes:
                response = client.get(f"{route}?theme={theme}")
                assert response.status_code == 200, f"Route {route} failed under theme {theme}"

    def test_htmx_todo_delete_declarative(self, client):
        todo = Todo.objects.create(title="HTMX Test Todo", text="Testing zero-reload deletion")
        delete_url = reverse('todo:delete', kwargs={'id': todo.id})

        # HTMX AJAX deletion
        response = client.post(delete_url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert response.content == b""
        assert not Todo.objects.filter(id=todo.id).exists()

    def test_plugin_templates_support(self):
        todo_plugin = registry.get_plugin('todo')
        assert todo_plugin is not None
        templates_map = todo_plugin.get_plugin_templates()
        assert 'bootstrap5' in templates_map
        assert 'tailwind' in templates_map

        all_templates = registry.get_all_plugin_templates()
        assert 'todo' in all_templates

    def test_navigation_parity_across_all_themes(self, client):
        """Verifies that all 3 themes provide complete navigation access including Apps."""
        for theme in ['bootstrap5', 'tailwind', 'minimal']:
            response = client.get(f"/?theme={theme}")
            assert response.status_code == 200
            content = response.content.decode('utf-8')
            assert 'href="/about/"' in content, f"About link missing in theme {theme}"
            assert 'href="/services/"' in content, f"Services link missing in theme {theme}"
            assert 'href="/products/"' in content, f"Products link missing in theme {theme}"
            assert 'href="/contact/"' in content, f"Contact link missing in theme {theme}"
            assert 'href="/todo/"' in content, f"Todo app link missing in theme {theme}"
            assert 'href="/crm/"' in content, f"CRM app link missing in theme {theme}"
            assert 'href="/erp/"' in content, f"ERP app link missing in theme {theme}"

    def test_shared_design_tokens_and_adapter_in_all_themes(self, client):
        """Verifies that theme-tokens.css and theme-adapter.css are linked in all themes."""
        for theme in ['bootstrap5', 'tailwind', 'minimal']:
            response = client.get(f"/?theme={theme}")
            assert response.status_code == 200
            content = response.content.decode('utf-8')
            assert 'theme-tokens.css' in content, f"theme-tokens.css not linked in {theme}"
            assert 'theme-adapter.css' in content, f"theme-adapter.css not linked in {theme}"

    def test_base_main_tag_structure_across_all_themes(self):
        """Verifies that <main> tags are opened and closed properly in all theme base templates."""
        for theme in ['bootstrap5', 'tailwind', 'minimal']:
            set_current_theme(theme)
            rendered = render_to_string('base.html', {'title': 'Main Tag Test'})
            assert '<main' in rendered, f"<main> tag missing in theme {theme}"
            assert '</main>' in rendered, f"</main> closing tag missing in theme {theme}"
            assert rendered.count('<main') == 1, f"Unexpected <main> count in theme {theme}"
            assert rendered.count('</main>') == 1, f"Unexpected </main> count in theme {theme}"

    def test_zero_custom_modal_hacks_in_task_runner(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(reverse('task_runner:list'))
        assert response.status_code == 200
        content = response.content.decode('utf-8')

        # Modal must be native Bootstrap 5
        assert 'data-bs-toggle="modal"' in content
        assert 'data-bs-target="#launchTaskModal"' in content
        assert 'data-bs-dismiss="modal"' in content
        assert 'btn-close' in content

        # Legacy hacks must be absent
        assert 'display: block !important' not in content
        assert '#launchTaskModal.in' not in content
        assert 'style="margin-right: 10px;"' not in content

    def test_theme_adapter_defines_container(self):
        """Verifies theme-adapter.css defines centered responsive container rules inside @layer."""
        adapter_path = Path(settings.BASE_DIR) / 'static' / 'css' / 'theme-adapter.css'
        css = adapter_path.read_text(encoding='utf-8')

        assert '@layer theme-adapter' in css
        assert '.container,' in css
        assert '.container-fluid,' in css
        assert 'margin-inline: auto;' in css
        assert '--bs-gutter-x' in css
        assert '--container-gutter-x' in css
        assert 'padding-inline:' in css
        for max_width in ('540px', '720px', '960px', '1140px', '1320px'):
            assert max_width in css, f"Expected responsive container max-width {max_width} in theme-adapter.css"

    def test_container_centering_across_all_themes(self, client, staff_user):
        """Verifies container adapter linkage and theme-specific centering rules across all themes."""
        client.force_login(staff_user)
        target_routes = ['/', reverse('crm:dashboard')]

        for theme in ['bootstrap5', 'tailwind', 'minimal']:
            for route in target_routes:
                response = client.get(f"{route}?theme={theme}")
                assert response.status_code == 200, f"{route} failed under theme {theme}"
                content = response.content.decode('utf-8')

                assert 'theme-adapter.css' in content, f"theme-adapter.css missing on {route} ({theme})"
                assert 'container' in content, f"No container class rendered on {route} ({theme})"

                if theme == 'tailwind':
                    assert re.search(
                        r"container:\s*\{\s*center:\s*true,\s*padding:\s*'1rem'",
                        content,
                    ), f"Tailwind container center/padding config missing on {route}"
                elif theme == 'minimal':
                    assert '--container-max-width: 1200px;' in content
                    assert '--container-gutter-x:' in content
                    assert 'var(--container-max-width' in content
                    assert 'margin-inline: auto;' in content
                elif theme == 'bootstrap5':
                    assert 'bootstrap@5.3.3' in content
