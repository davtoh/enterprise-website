import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

from django.apps import apps
import pytest

from cms.blocks import CMSStreamBlock, _load_optional_block
from erp.plugin import ERPPlugin
from home.services import ingest_website_contact_submission
from intelligent_tracker_hub.plugin import IntelligentTrackerPlugin
from plugin_registry.scaffolding import (
    CORE_ALWAYS_ON_APPS,
    ProjectGenerator,
    SiteManifest,
    resolve_plugin_dependencies,
    suggest_manifest_from_prompt,
)


class TestSiteManifest:
    """Tests for SiteManifest validation, dependency closure, and JSON round-trips."""

    def test_valid_slug_normalization_and_defaults(self):
        manifest = SiteManifest(project_name="My-Enterprise-Site", plugins=[])
        manifest.validate()
        assert manifest.project_name == "my_enterprise_site"
        assert manifest.display_name == "My Enterprise Site"
        assert manifest.theme == "bootstrap5"
        assert manifest.database == "sqlite"
        assert manifest.languages == ["en", "es"]
        assert manifest.enable_labs is False

    @pytest.mark.parametrize("bad_name", ["123-bad", "bad name", "", "django", "class", "site"])
    def test_invalid_project_name_rejected(self, bad_name):
        manifest = SiteManifest(project_name=bad_name, plugins=[])
        with pytest.raises(ValueError):
            manifest.validate()

    def test_invalid_theme_database_and_locale_rejected(self):
        with pytest.raises(ValueError, match="Unsupported theme"):
            SiteManifest(project_name="acme_site", theme="bulma", plugins=[]).validate()
        with pytest.raises(ValueError, match="Unsupported database"):
            SiteManifest(project_name="acme_site", database="oracle", plugins=[]).validate()
        with pytest.raises(ValueError, match="Unsupported language"):
            SiteManifest(project_name="acme_site", languages=["zz"], plugins=[]).validate()

    def test_languages_always_include_english(self):
        manifest = SiteManifest(project_name="acme_site", languages=["es", "fr"], plugins=[])
        manifest.validate()
        assert manifest.languages == ["en", "es", "fr"]

    def test_webprogram_enables_labs_flag(self):
        manifest = SiteManifest(project_name="acme_site", plugins=["webprogram"])
        manifest.validate()
        assert manifest.enable_labs is True

    def test_transitive_plugin_dependency_resolution(self):
        assert ERPPlugin.dependencies == ["crm"]
        assert set(IntelligentTrackerPlugin.dependencies) == {"crm", "video_gallery", "rest_api"}
        assert resolve_plugin_dependencies(["erp"]) == ["crm", "erp"]
        assert resolve_plugin_dependencies(["intelligent_tracker_hub"]) == [
            "rest_api",
            "video_gallery",
            "crm",
            "intelligent_tracker_hub",
        ]

    def test_resolved_enterprise_apps_filters_installed_configs(self):
        manifest = SiteManifest(project_name="acme_site", plugins=["erp"])
        manifest.validate()
        app_configs = manifest.resolved_enterprise_apps()
        for core_app in CORE_ALWAYS_ON_APPS:
            assert any(cfg.startswith(f"{core_app}.") for cfg in app_configs)
        assert "crm.apps.CrmConfig" in app_configs
        assert "erp.apps.ErpConfig" in app_configs
        assert "polls.apps.PollsConfig" not in app_configs

    def test_json_manifest_round_trip(self, tmp_path):
        manifest_path = tmp_path / "site_manifest.json"
        original = SiteManifest(
            project_name="acme-portal",
            display_name="Acme Portal",
            theme="tailwind",
            languages=["es", "pt"],
            plugins=["erp", "polls"],
            database="postgres",
            include_docker=False,
            homepage_headline="Acme Operations",
        )
        original.validate()
        original.write_json_file(manifest_path)

        reloaded = SiteManifest.from_json_file(manifest_path)
        assert reloaded.project_name == "acme_portal"
        assert reloaded.theme == "tailwind"
        assert reloaded.database == "postgres"
        assert reloaded.languages == ["en", "es", "pt"]
        assert reloaded.plugins == ["polls", "crm", "erp"]
        assert reloaded.include_docker is False
        assert reloaded.homepage_headline == "Acme Operations"


class TestAIBlueprintAdvisor:
    """Tests for optional --ai blueprint advisor and deterministic offline fallback."""

    def test_ai_advisor_heuristic_erp_prompt(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        manifest = suggest_manifest_from_prompt(
            "Build an ERP inventory and invoicing portal for our sales team."
        )
        assert "erp" in manifest.plugins
        assert "crm" in manifest.plugins
        assert manifest.homepage_headline

    def test_ai_advisor_heuristic_security_tailwind_postgres(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        manifest = suggest_manifest_from_prompt(
            "AI security camera surveillance SOC with Tailwind, Postgres, and Spanish support."
        )
        assert set(manifest.plugins) >= {"intelligent_tracker_hub", "crm", "video_gallery", "rest_api"}
        assert manifest.theme == "tailwind"
        assert manifest.database == "postgres"
        assert manifest.languages == ["en", "es"]

    def test_ai_advisor_parses_mocked_gemini_response(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")

        class _FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                suggestion = {
                    "plugins": ["erp", "polls"],
                    "theme": "minimal",
                    "languages": ["en", "fr"],
                    "database": "mysql",
                    "homepage_headline": "Global Supply Hub",
                    "homepage_subheadline": "Streamlined catalog and customer feedback.",
                }
                envelope = {
                    "candidates": [
                        {"content": {"parts": [{"text": f"```json\n{json.dumps(suggestion)}\n```"}]}}
                    ]
                }
                return json.dumps(envelope).encode("utf-8")

        monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=10: _FakeResponse())
        manifest = suggest_manifest_from_prompt("Global supply hub with surveys")
        assert manifest.theme == "minimal"
        assert manifest.database == "mysql"
        assert manifest.languages == ["en", "fr"]
        assert manifest.plugins == ["polls", "crm", "erp"]
        assert manifest.homepage_headline == "Global Supply Hub"

    def test_ai_advisor_falls_back_on_network_error(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")

        def _fail_urlopen(req, timeout=10):
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(urllib.request, "urlopen", _fail_urlopen)
        manifest = suggest_manifest_from_prompt("Video media gallery with Tailwind")
        assert "video_gallery" in manifest.plugins
        assert manifest.theme == "tailwind"


@pytest.mark.django_db
class TestOptionalAppGuards:
    """Tests ensuring core apps degrade gracefully when optional plugins are omitted."""

    def test_ingest_contact_without_todo_installed(self, monkeypatch):
        orig_is_installed = apps.is_installed
        monkeypatch.setattr(apps, "is_installed", lambda name: False if name == "todo" else orig_is_installed(name))

        contact, lead, interaction, followup_todo = ingest_website_contact_submission(
            name="Ada Lovelace",
            email="ada@example.com",
            subject="Engine Inquiry",
            message="Testing optional todo guard.",
        )
        assert contact is not None
        assert lead is not None
        assert interaction is not None
        assert followup_todo is None

    def test_ingest_contact_without_crm_or_todo_installed(self, monkeypatch):
        orig_is_installed = apps.is_installed
        monkeypatch.setattr(
            apps,
            "is_installed",
            lambda name: False if name in ("crm", "todo") else orig_is_installed(name),
        )
        result = ingest_website_contact_submission(
            name="Alan Turing",
            email="alan@example.com",
            subject="Core Only",
            message="No CRM or Todo installed.",
        )
        assert result == (None, None, None, None)

    def test_cms_optional_block_loader_guards_uninstalled_apps(self, monkeypatch):
        assert "product_showcase" in CMSStreamBlock.base_blocks
        orig_is_installed = apps.is_installed
        monkeypatch.setattr(apps, "is_installed", lambda name: False if name == "erp" else orig_is_installed(name))
        assert _load_optional_block("erp", "erp.blocks", "ProductShowcaseBlock") is None


def _run_generated_manage(project_dir, *args):
    """Run manage.py inside an isolated generated project without inheriting parent settings."""
    env = os.environ.copy()
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env["USE_SQLITE"] = "True"
    env["DEBUG"] = "True"
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class TestProjectGenerator:
    """Isolated TemporaryDirectory tests for ProjectGenerator and rendered configs."""

    def test_generate_minimal_project_passes_check_and_migrate(self, tmp_path):
        manifest = SiteManifest(
            project_name="acme_minimal",
            display_name="Acme Minimal",
            theme="minimal",
            languages=["en"],
            plugins=[],
            database="sqlite",
            include_docker=False,
        )
        dest = ProjectGenerator(manifest).generate(tmp_path / "acme_minimal")

        assert (dest / "manage.py").is_file()
        assert (dest / "acme_minimal" / "settings" / "base.py").is_file()
        assert (dest / "site_manifest.json").is_file()
        assert not (dest / "docker-compose.yml").exists()
        assert not (dest / "crm").exists()
        assert not (dest / "erp").exists()

        check_res = _run_generated_manage(dest, "check")
        assert check_res.returncode == 0, check_res.stderr

        migrate_res = _run_generated_manage(dest, "migrate", "--noinput")
        assert migrate_res.returncode == 0, migrate_res.stderr

    def test_generate_selective_enterprise_project_passes_check_and_migrate(self, tmp_path):
        manifest = SiteManifest(
            project_name="acme_ops",
            display_name="Acme Operations",
            theme="tailwind",
            languages=["en", "es"],
            plugins=["erp", "intelligent_tracker_hub"],
            database="sqlite",
            include_docker=True,
        )
        dest = ProjectGenerator(manifest).generate(tmp_path / "acme_ops")

        assert (dest / "docker-compose.yml").is_file()
        assert (dest / "crm").is_dir()
        assert (dest / "erp").is_dir()
        assert (dest / "video_gallery").is_dir()
        assert (dest / "rest_api" / "v1_urls.py").is_file()
        assert not (dest / "polls").exists()

        check_res = _run_generated_manage(dest, "check")
        assert check_res.returncode == 0, check_res.stderr

        migrate_res = _run_generated_manage(dest, "migrate", "--noinput")
        assert migrate_res.returncode == 0, migrate_res.stderr

    def test_generate_refuses_non_empty_target_without_overwrite(self, tmp_path):
        target = tmp_path / "existing_site"
        target.mkdir()
        (target / "README.txt").write_text("keep me", encoding="utf-8")

        manifest = SiteManifest(project_name="existing_site", plugins=[])
        with pytest.raises(FileExistsError):
            ProjectGenerator(manifest).generate(target)


