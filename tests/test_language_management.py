import io
from unittest.mock import patch
import pytest
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from language_management.management.commands.auto_translate import Command as AutoTranslateCommand


@pytest.mark.django_db
class TestLanguageManagement:
    """Tests for language switcher and auto_translate command."""

    def test_language_management_index_view(self, client):
        response = client.get(reverse("language_management:index"))
        assert response.status_code == 200
        assert response.context["title"] == "Language Management"
        assert '<select name="language"' in response.content.decode()

    def test_language_switch_endpoint_spanish(self, client):
        # Django standard i18n setlang endpoint
        url = reverse("set_language")
        response = client.post(url, {"language": "es", "next": "/"})
        assert response.status_code == 302
        assert response.cookies.get("django_language") is not None
        assert response.cookies["django_language"].value == "es"

    def test_language_switch_endpoint_french(self, client):
        url = reverse("set_language")
        response = client.post(url, {"language": "fr", "next": "/about/"})
        assert response.status_code == 302
        assert response.cookies["django_language"].value == "fr"

    @override_settings(CSRF_TRUSTED_ORIGINS=[])
    def test_language_switch_dynamic_port_same_origin(self):
        """Verify that language switch succeeds on any dynamic port (e.g. 3000) via Host header."""
        client = Client(enforce_csrf_checks=True)
        get_res = client.get("/", HTTP_HOST="localhost:3000")
        csrf_token = get_res.cookies.get("csrftoken").value
        response = client.post(
            reverse("set_language"),
            {"language": "es", "next": "/", "csrfmiddlewaretoken": csrf_token},
            HTTP_HOST="localhost:3000",
            HTTP_ORIGIN="http://localhost:3000",
            headers={"referer": "http://localhost:3000/"},
        )
        assert response.status_code == 302
        assert response.cookies.get("django_language") is not None
        assert response.cookies["django_language"].value == "es"

    @override_settings(CSRF_TRUSTED_ORIGINS=["https://trusted.example.com"])
    def test_language_switch_csrf_trusted_origin_fallback(self):
        """Verify that language switch succeeds when Host differs from Origin but matches CSRF_TRUSTED_ORIGINS."""
        client = Client(enforce_csrf_checks=True)
        get_res = client.get("/")
        csrf_token = get_res.cookies.get("csrftoken").value
        response = client.post(
            reverse("set_language"),
            {"language": "fr", "next": "/", "csrfmiddlewaretoken": csrf_token},
            HTTP_HOST="testserver",
            HTTP_ORIGIN="https://trusted.example.com",
            headers={"referer": "https://trusted.example.com/"},
        )
        assert response.status_code == 302
        assert response.cookies.get("django_language") is not None
        assert response.cookies["django_language"].value == "fr"

    def test_auto_translate_placeholder_protection(self):
        cmd = AutoTranslateCommand()
        original = "Welcome, %(username)s! You have {{ count }} notifications and %s items."
        safe_text, placeholders = cmd._protect_placeholders(original)

        assert "%(username)s" not in safe_text
        assert "{{ count }}" not in safe_text
        assert "%s" not in safe_text


        # Restore
        restored = cmd._restore_placeholders(safe_text, placeholders)
        assert restored == original

    def test_auto_translate_invalid_language(self):
        out = io.StringIO()
        err = io.StringIO()
        call_command("auto_translate", lang="invalid_code", stdout=out, stderr=err)
        assert "is not in settings.LANGUAGES" in err.getvalue()

    @patch("polib.POFile.save")
    @patch.object(AutoTranslateCommand, "_translate_mymemory")
    def test_auto_translate_with_mocked_backend(self, mock_translate, mock_save):
        mock_translate.return_value = "Texto traducido de prueba"
        out = io.StringIO()
        # Run with max=1 and no-compile to test the pipeline safely without mutating disk
        call_command("auto_translate", lang="es", max=1, no_compile=True, stdout=out)
        output = out.getvalue()
        assert "Starting Auto-Translation Baseline Engine" in output
        assert "Processing [es]" in output
        assert mock_save.called

    @patch("polib.POFile.save")
    def test_auto_translate_unfuzzy_all(self, mock_save):
        out = io.StringIO()
        call_command("auto_translate", lang="es", unfuzzy_all=True, no_compile=True, stdout=out)
        output = out.getvalue()
        assert "Stripping fuzzy flags from non-empty translated entries" in output
        assert "Unfuzzied" in output

    def test_auto_translate_deepl_without_key(self):
        cmd = AutoTranslateCommand()
        assert cmd._translate_deepl("Hello", "es") is None

    @patch("requests.post")
    def test_auto_translate_deepl_with_key(self, mock_post, settings):
        settings.DEEPL_AUTH_KEY = "test-key:fx"
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"translations": [{"text": "Hola"}]}

        cmd = AutoTranslateCommand()
        assert cmd._translate_deepl("Hello", "es") == "Hola"
        assert cmd._translate_deepl("Hello", "pt") == "Hola"

    def test_auto_translate_openai_without_key(self):
        cmd = AutoTranslateCommand()
        assert cmd._translate_openai("Hello", "es") is None

    @patch("requests.post")
    def test_auto_translate_openai_with_key(self, mock_post, settings):
        settings.OPENAI_API_KEY = "test-openai-key"
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Hola mundo"}}]
        }

        cmd = AutoTranslateCommand()
        assert cmd._translate_openai("Hello world", "es") == "Hola mundo"

    @patch.object(AutoTranslateCommand, "_translate_mymemory")
    def test_auto_translate_string_dispatcher(self, mock_mymemory):
        mock_mymemory.return_value = "Hola [[PH0]]"
        cmd = AutoTranslateCommand()
        res = cmd._translate_string("Hello %(name)s", "es", backend="mymemory")
        assert res == "Hola %(name)s"

    @patch("urllib.request.urlopen")
    def test_auto_translate_google_web_backend(self, mock_urlopen):
        mock_res = io.BytesIO(b'[[["Hola mundo", "Hello world", null, null, 1]]]')
        mock_urlopen.return_value.__enter__.return_value = mock_res
        cmd = AutoTranslateCommand()
        result = cmd._translate_google("Hello world", "es")
        assert result == "Hola mundo"

    @patch("urllib.request.urlopen")
    def test_auto_translate_gemini_backend_with_key(self, mock_urlopen, settings):
        settings.GEMINI_API_KEY = "dummy-gemini-key"
        res_payload = b'{"candidates": [{"content": {"parts": [{"text": "[{\\"id\\": 0, \\"translation\\": \\"Bonjour le monde\\"}]"}]}}]}'
        mock_urlopen.return_value.__enter__.return_value = io.BytesIO(res_payload)
        cmd = AutoTranslateCommand()
        result = cmd._translate_gemini("Hello world", "fr")
        assert result == "Bonjour le monde"

    @patch("urllib.request.urlopen")
    def test_mymemory_circuit_breaker_on_429(self, mock_urlopen):
        import urllib.error
        from language_management.services.translator import RateLimitExceededError

        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {}, None
        )
        cmd = AutoTranslateCommand()
        with pytest.raises(RateLimitExceededError):
            cmd._translate_mymemory("Hello", "es")


