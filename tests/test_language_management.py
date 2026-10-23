import io
from unittest.mock import patch
import pytest
from django.core.management import call_command
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

    @patch.object(AutoTranslateCommand, "_translate_mymemory")
    def test_auto_translate_with_mocked_backend(self, mock_translate):
        mock_translate.return_value = "Texto traducido de prueba"
        out = io.StringIO()
        # Run with max=1 and no-compile to test the pipeline safely
        call_command("auto_translate", lang="es", max=1, no_compile=True, stdout=out)
        output = out.getvalue()
        assert "Starting Auto-Translation Baseline Engine" in output
        assert "Processing [es]" in output

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

