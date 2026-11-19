# Changelog

## [2026-11-19] feat: Milestone 18.3: CI Package Build, Executable Docs & Sign-Off
- **Type**: feat
- **Summary**: Added editable CLI install and smoke test to GitHub Actions CI, documented create-enterprise-site quickstart and Scenario Combinations Matrix in README.md and documentation/create_site.md, marked Milestone 18 complete in milestone_plan.md, and added pyproject/version/doc-flag-parity tests.
- **Files** (5):
  - `.github/workflows/ci.yml`
  - `README.md`
  - `documentation/create_site.md`
  - `milestone_plan.md`
  - `tests/test_create_enterprise_site_cli.py`
- **Verification**: .venv/Scripts/python.exe -m pytest tests/test_create_enterprise_site_cli.py tests/test_create_site.py tests/test_create_site_command.py

## [2026-11-19] feat: Milestone 18.2: create-enterprise-site Standalone CLI & PEP 621 Packaging
- **Type**: feat
- **Summary**: Implemented create_enterprise_site.cli/main, python -m create_enterprise_site entrypoint, PEP 621 pyproject.toml, MANIFEST.in, and E2E CLI tests.
- **Files** (5):
  - `tests/test_create_enterprise_site_cli.py`
  - `MANIFEST.in`
  - `create_enterprise_site/__main__.py`
  - `create_enterprise_site/cli.py`
  - `pyproject.toml`
- **Verification**: .venv/Scripts/python.exe -m pytest tests/test_create_enterprise_site_cli.py tests/test_create_site.py tests/test_create_site_command.py

## [2026-11-19] feat: Milestone 18.1: Pure-Stdlib Scaffolding Engine, Shared CLI Runner & Template Fetcher
- **Type**: feat
- **Summary**: Decoupled Django imports from plugin_registry.scaffolding, extracted shared cli_runner.py, and added create_enterprise_site/fetcher.py with SHA-256 and Zip-Slip/Tar-Slip protection.
- **Files** (10):
  - `.TODO/create_enterprise_site_pip_cli.md`
  - `AGENTS.md`
  - `plugin_registry/__init__.py`
  - `plugin_registry/management/commands/create_site.py`
  - `plugin_registry/scaffolding/__init__.py`
  - `plugin_registry/scaffolding/generator.py`
  - `plugin_registry/scaffolding/manifest.py`
  - `create_enterprise_site/`
  - ... (+2 more)
- **Verification**: pytest tests/test_create_enterprise_site_cli.py tests/test_create_site.py tests/test_create_site_command.py

## [2026-11-19] feat: Milestone 17.3: manage.py create_site CLI Wizard & Docs
- **Type**: feat
- **Summary**: Implemented interactive and non-interactive manage.py create_site wizard, documentation/create_site.md, and E2E CLI tests.
- **Files** (5):
  - `milestone_plan.md`
  - `tests/test_create_site.py`
  - `documentation/create_site.md`
  - `plugin_registry/management/`
  - `tests/test_create_site_command.py`
- **Verification**: pytest tests/test_create_site.py tests/test_create_site_command.py

## [2026-11-19] feat: Milestone 17.2: Project Scaffolding Generator Engine
- **Type**: feat
- **Summary**: Added split-settings, URLconf, env, requirements, and Docker renderers plus ProjectGenerator and optional task_runner/polls guards.
- **Files** (8):
  - `crm/tasks.py`
  - `custom_tags/templatetags/present.py`
  - `erp/tasks.py`
  - `plugin_registry/scaffolding/__init__.py`
  - `tests/test_create_site.py`
  - `plugin_registry/scaffolding/generator.py`
  - `plugin_registry/scaffolding/renderers.py`
  - `plugin_registry/scaffolding/settings_renderers.py`
- **Verification**: pytest tests/test_create_site.py tests/test_plugin_registry.py tests/test_home.py tests/test_cms.py

## [2026-11-19] feat: create_site Milestone 1: SiteManifest, Dependency Resolver & AI Blueprint Advisor
- **Type**: feat
- **Summary**: Added SiteManifest schema/JSON IO, transitive AppPlugin dependency resolver, optional --ai blueprint advisor with offline heuristic fallback, and optional-app guards in home/services.py and cms/blocks.py.
- **Files** (8):
  - `.TODO/create_site_scaffolding_wizard.md`
  - `AGENTS.md`
  - `cms/blocks.py`
  - `erp/plugin.py`
  - `home/services.py`
  - `intelligent_tracker_hub/plugin.py`
  - `plugin_registry/scaffolding/`
  - `tests/test_create_site.py`
- **Verification**: pytest tests/test_create_site.py tests/test_plugin_registry.py tests/test_home.py tests/test_cms.py

## [2026-11-16] refactor: Step 5 Milestone 3: Modularity Budget Paydown & Master Roadmap Sign-Off
- **Type**: refactor
- **Summary**: Decomposed erp/pdf.py, intelligent_tracker_hub/api/*.py (with shared _helpers.py), and dashboard.html into 7 partials; all 468 pytest tests and modularity audits pass.
- **Files** (8):
  - `erp/pdf.py`
  - `intelligent_tracker_hub/api/access_control.py`
  - `intelligent_tracker_hub/api/security_events.py`
  - `intelligent_tracker_hub/api/video_evidence.py`
  - `intelligent_tracker_hub/api/video_streaming.py`
  - `intelligent_tracker_hub/templates/intelligent_tracker_hub/dashboard.html`
  - `intelligent_tracker_hub/api/_helpers.py`
  - `intelligent_tracker_hub/templates/intelligent_tracker_hub/partials/`
- **Verification**: pytest

## [2026-11-16] feat: Step 5 M2: Ecosystem Ops (django-filter, django-import-export & django-htmx)
- **Type**: feat
- **Summary**: Added FilterSets, Unfold ImportExportModelAdmin resources, and HTMX partial table rendering across crm, erp, and location_management.
- **Files** (27):
  - `crm/admin.py`
  - `crm/templates/crm/company_list.html`
  - `crm/templates/crm/contact_list.html`
  - `crm/templates/crm/lead_list.html`
  - `crm/views/companies.py`
  - `crm/views/contacts.py`
  - `crm/views/leads.py`
  - `erp/admin.py`
  - ... (+19 more)
- **Verification**: pytest tests/crm/ tests/erp/ tests/test_home.py

## [2026-11-16] feat: Step 5 M1: Unified /api/v1/ (drf-spectacular) & AppPlugin.api_urlpatterns
- **Type**: feat
- **Summary**: Added drf-spectacular, django-filter, django-import-export, and django-htmx; mounted /api/v1/schema/, /api/v1/docs/, /api/v1/redoc/, and active plugin API routes via get_active_api_urlpatterns().
- **Files** (12):
  - `.TODO/step_5_unified_api_and_modularity_paydown.md`
  - `AGENTS.md`
  - `enterprise_website/settings/apps.py`
  - `enterprise_website/settings/base.py`
  - `enterprise_website/settings/integrations.py`
  - `enterprise_website/urls.py`
  - `plugin_registry/registry.py`
  - `requirements/base.txt`
  - ... (+4 more)
- **Verification**: pytest tests/test_rest_api.py tests/test_plugin_registry.py tests/tracker/

## [2026-11-16] feat: Step 4 Milestone 3: ActionItem Promotion & SiteUser Locale/Timezone Sync
- **Type**: feat
- **Summary**: Promoted Todo to ActionItem with GenericForeignKey, linked contact leads in home/services.py, and synced SiteUser preferred_language and timezone.
- **Files** (19):
  - `enterprise_website/settings/base.py`
  - `enterprise_website/urls.py`
  - `home/services.py`
  - `language_management/views.py`
  - `tests/test_home.py`
  - `tests/test_timezone_management.py`
  - `tests/test_todo.py`
  - `tests/test_user_management.py`
  - ... (+11 more)
- **Verification**: pytest tests/test_video_gallery.py tests/test_polls.py tests/test_todo.py tests/crm/ tests/erp/ tests/test_timezone_management.py tests/test_user_management.py tests/test_home.py tests/test_cms.py

## [2026-11-15] feat: Step 4 Milestone 2: ERP Modular Models, Public Catalog & CRM Invoice Link
- **Type**: feat
- **Summary**: Split erp/models.py into erp/models/ package, added Product.is_published/public_summary, ProductShowcaseBlock, dynamic ProductsView catalog, and Invoice CRM backfill.
- **Files** (16):
  - `cms/blocks.py`
  - `erp/forms.py`
  - `erp/models.py`
  - `erp/plugin.py`
  - `erp/views/invoices.py`
  - `home/templates/home/products.html`
  - `home/views.py`
  - `tests/erp/test_invoices_and_pdf.py`
  - ... (+8 more)
- **Verification**: pytest tests/erp/ tests/crm/ tests/test_home.py tests/test_cms.py
