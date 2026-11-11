import re
from html.parser import HTMLParser
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
        """Verifies theme-adapter.css defines centered responsive container rules inside @layer adapter."""
        adapter_path = Path(settings.BASE_DIR) / 'static' / 'css' / 'theme-adapter.css'
        css = adapter_path.read_text(encoding='utf-8')

        assert '@layer adapter' in css
        assert '.container,' in css
        assert '.container-fluid,' in css
        assert 'margin-inline: auto;' in css
        assert '--bs-gutter-x' in css
        assert '--container-gutter-x' in css
        assert 'padding-inline:' in css
        for max_width in ('540px', '720px', '960px', '1140px', '1320px'):
            assert max_width in css, f"Expected responsive container max-width {max_width} in theme-adapter.css"

    def test_css_cascade_layer_hierarchy(self, client):
        """Verifies formal @layer hierarchy across tokens, adapter, and theme style partials."""
        tokens_css = (Path(settings.BASE_DIR) / 'static' / 'css' / 'theme-tokens.css').read_text(encoding='utf-8')
        adapter_css = (Path(settings.BASE_DIR) / 'static' / 'css' / 'theme-adapter.css').read_text(encoding='utf-8')

        expected_order = '@layer tokens, framework, adapter, components, utilities;'
        assert expected_order in tokens_css
        assert '@layer tokens' in tokens_css
        assert '@layer components' in tokens_css

        assert expected_order in adapter_css
        assert '@layer adapter' in adapter_css
        assert '@layer utilities' in adapter_css
        assert '!important' not in adapter_css
        assert adapter_css.index('.border-0') < adapter_css.index('.border-start')
        assert adapter_css.index('.d-none') < adapter_css.index('.d-sm-inline-block')

        bs5_content = client.get('/?theme=bootstrap5').content.decode('utf-8')
        assert expected_order in bs5_content
        assert 'layer(framework)' in bs5_content
        assert 'bootstrap@5.3.3/dist/css/bootstrap.min.css") layer(framework)' in bs5_content

        minimal_content = client.get('/?theme=minimal').content.decode('utf-8')
        assert '@layer framework' in minimal_content
        assert '@layer adapter' in minimal_content

        tailwind_content = client.get('/?theme=tailwind').content.decode('utf-8')
        assert 'preflight: false' in tailwind_content
        assert '@layer framework' in tailwind_content

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


class _ContainerDOMParser(HTMLParser):
    """HTML parser extracting container divs and linked stylesheet hrefs."""

    def __init__(self):
        super().__init__()
        self.containers, self.stylesheets, self._in_main = [], [], False

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        if tag == 'main':
            self._in_main = True
        elif tag == 'link' and attr_map.get('rel') == 'stylesheet':
            self.stylesheets.append(attr_map.get('href', ''))
        elif tag == 'div':
            classes = attr_map.get('class', '').split()
            if 'container' in classes or 'container-fluid' in classes:
                self.containers.append({
                    'classes': classes,
                    'style': attr_map.get('style', ''),
                    'in_main': self._in_main,
                })

    def handle_endtag(self, tag):
        if tag == 'main':
            self._in_main = False


@pytest.mark.django_db
class TestThemeHygieneAndLayout:

    def test_zero_important_in_application_stylesheets(self):
        """Ensures application CSS and theme <style> blocks avoid !important outside [x-cloak]."""
        base = Path(settings.BASE_DIR)
        vendor_css = {
            'animate.min.css', 'bootstrap.css', 'font-awesome.min.css',
            'linearicons.css', 'magnific-popup.css', 'nice-select.css',
        }
        excluded = {'.venv', 'staticfiles', 'htmlcov', 'node_modules'}
        app_css = [
            p for p in base.rglob('*.css')
            if not (excluded & set(p.parts)) and p.name not in vendor_css
        ]
        assert {'theme-tokens.css', 'theme-adapter.css'} <= {p.name for p in app_css}

        for css_path in app_css:
            cleaned = re.sub(r'/\*.*?\*/', '', css_path.read_text(encoding='utf-8'), flags=re.S)
            assert '!important' not in cleaned, f"Disallowed !important in {css_path.relative_to(base)}"

        for theme in settings.AVAILABLE_THEMES:
            partial = base / 'templates' / 'themes' / theme / 'partials' / 'styles.html'
            for block in re.findall(r'<style[^>]*>(.*?)</style>', partial.read_text(encoding='utf-8'), flags=re.S | re.I):
                cleaned = re.sub(r'\[x-cloak\]\s*\{[^}]*\}', '', re.sub(r'/\*.*?\*/', '', block, flags=re.S), flags=re.S)
                assert '!important' not in cleaned, f"Disallowed !important in {theme} styles.html"

    def test_container_dom_centered_layout_in_crm_and_todo(self, client, staff_user):
        """Verifies parsed DOM containers in CRM and Todo inherit centered layout across themes."""
        client.force_login(staff_user)
        routes = [
            (reverse('todo:index'), 'container'),
            (reverse('todo:add'), 'container'),
            (reverse('crm:dashboard'), 'container-fluid'),
        ]
        disallowed = {'mx-0', 'ml-0', 'mr-0', 'ms-0', 'me-0'}

        for theme in settings.AVAILABLE_THEMES:
            for url, expected_cls in routes:
                response = client.get(f"{url}?theme={theme}")
                assert response.status_code == 200
                parser = _ContainerDOMParser()
                parser.feed(response.content.decode('utf-8'))
                nodes = [c for c in parser.containers if c['in_main'] and expected_cls in c['classes']]
                assert nodes, f"Missing <div class='{expected_cls}'> in <main> for {url} ({theme})"
                assert any('theme-adapter.css' in href for href in parser.stylesheets)
                assert any('theme-tokens.css' in href for href in parser.stylesheets)
                for node in nodes:
                    assert not (disallowed & set(node['classes'])), f"Uncentered class on {url} ({theme})"
                    assert not re.search(r'margin-(left|right|inline)\s*:\s*0', node['style'])
