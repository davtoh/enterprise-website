import io
import sys

from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from plugin_registry.scaffolding import SiteManifest
from tests.test_create_site import _run_generated_manage


class TestCreateSiteCommand:
    """End-to-end tests for `manage.py create_site` CLI flags, stdin prompts, manifests, and --ai."""

    def test_non_interactive_cli_flags_and_dependency_closure(self, tmp_path):
        target = tmp_path / "acme_erp_site"
        out = io.StringIO()
        call_command(
            "create_site",
            "acme_erp_site",
            "--no-input",
            "--display-name",
            "Acme ERP",
            "--theme",
            "tailwind",
            "--languages",
            "en,es",
            "--plugins",
            "erp",
            "--database",
            "sqlite",
            "--no-docker",
            "--target-dir",
            str(target),
            stdout=out,
        )

        assert (target / "manage.py").is_file()
        assert (target / "crm").is_dir()
        assert (target / "erp").is_dir()
        assert not (target / "docker-compose.yml").exists()
        assert "Next Steps:" in out.getvalue()

        check_res = _run_generated_manage(target, "check")
        assert check_res.returncode == 0, check_res.stderr

    def test_dump_manifest_dry_run_and_from_manifest_round_trip(self, tmp_path):
        manifest_path = tmp_path / "exported_manifest.json"
        target = tmp_path / "from_manifest_site"
        out = io.StringIO()

        call_command(
            "create_site",
            "from_manifest_site",
            "--no-input",
            "--plugins",
            "polls",
            "--theme",
            "minimal",
            "--no-docker",
            "--dump-manifest",
            str(manifest_path),
            "--dry-run",
            stdout=out,
        )
        assert manifest_path.is_file()
        assert not target.exists()

        call_command(
            "create_site",
            "--from-manifest",
            str(manifest_path),
            "--target-dir",
            str(target),
            stdout=out,
        )
        assert (target / "manage.py").is_file()
        assert (target / "polls").is_dir()
        assert not (target / "crm").exists()

    def test_ai_flag_heuristic_mode_generates_site(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        target = tmp_path / "ai_security_site"
        out = io.StringIO()
        call_command(
            "create_site",
            "ai_security_site",
            "--no-input",
            "--ai",
            "Security camera surveillance portal with CRM and Spanish support",
            "--target-dir",
            str(target),
            stdout=out,
        )
        saved = SiteManifest.from_json_file(target / "site_manifest.json")
        assert "intelligent_tracker_hub" in saved.plugins
        assert "crm" in saved.plugins
        assert "es" in saved.languages

    def test_interactive_stdin_wizard_prompts(self, tmp_path, monkeypatch):
        target = tmp_path / "wizard_site"
        answers = "\n".join(
            [
                "wizard_site",
                "Wizard Site",
                "Interactive test site",
                str(target),
                "bootstrap5",
                "en,fr",
                "todo",
                "sqlite",
                "n",
            ]
        ) + "\n"
        monkeypatch.setattr(sys, "stdin", io.StringIO(answers))

        out = io.StringIO()
        call_command("create_site", stdout=out)

        assert (target / "manage.py").is_file()
        assert (target / "todo").is_dir()
        assert not (target / "docker-compose.yml").exists()
        saved = SiteManifest.from_json_file(target / "site_manifest.json")
        assert saved.languages == ["en", "fr"]
        assert saved.plugins == ["todo"]

    def test_invalid_project_name_raises_command_error(self):
        with pytest.raises(CommandError):
            call_command("create_site", "django", "--no-input", "--dry-run")
