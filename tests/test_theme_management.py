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
