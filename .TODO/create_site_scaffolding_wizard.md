# Milestone 17 Implementation Plan: `create_site` Composable Scaffolding Wizard

**Plan Slug:** `create_site_scaffolding_wizard`  
**Milestone Reference:** `milestone_plan.md` (Milestone 17)  
**Architecture Reference:** `docs/ARCHITECTURE.md` & `documentation/plugin_system.md`  
**Selected Tier:** Tier 3 — Composable Manifest Engine (Interactive + Non-Interactive CLI Flags, Split-Settings & `AppPlugin v2` Dependency Resolver, Declarative JSON Manifest `--from-manifest` / `--dump-manifest`, Optional `--ai` Blueprint Advisor)  
**Execution Mode:** 1-Milestone-Per-Turn Execution Gate (`plan_engine.py`)

---

## 1. Executive Summary

This plan implements **Milestone 17 (`manage.py create_site`)** as a modular, deterministic, and Milestone 18-ready (`create-enterprise-site` CLI) scaffolding engine under `plugin_registry/scaffolding/` and `plugin_registry/management/commands/create_site.py`. It delivers the feature across 3 cohesive, vertically verified milestones:

1. **Milestone 1 (Composable `SiteManifest` Contract, Plugin Dependency Resolver, AI Blueprint Advisor & Cross-App Optionality Guards — ACTIVE EXECUTION TARGET)**: Declare explicit `AppPlugin.dependencies` (`erp` $\to$ `crm`, `intelligent_tracker_hub` $\to$ `crm`, `video_gallery`, `rest_api`), add graceful optional-app guards in `home/services.py` and `cms/blocks.py`, build `SiteManifest` with validation, transitive dependency resolution, and JSON round-trip export/import (`plugin_registry/scaffolding/manifest.py`), and implement the optional `--ai` blueprint advisor with offline deterministic heuristic fallback (`plugin_registry/scaffolding/ai_advisor.py`).
2. **Milestone 2 (Project Scaffolding Generator Engine — DEFERRED TO NEXT TURN / MILESTONE)**: Implement modular split-settings, URLs, `.env.example`, `requirements.txt`, and `docker-compose.yml` renderers (`plugin_registry/scaffolding/renderers.py`) alongside `ProjectGenerator` (`plugin_registry/scaffolding/generator.py`) to materialize clean, runnable standalone Django projects into target directories with automated `manage.py check` and `migrate` verification.
3. **Milestone 3 (`manage.py create_site` Interactive & Non-Interactive CLI Wizard & Documentation — DEFERRED TO NEXT TURN / MILESTONE)**: Implement `plugin_registry/management/commands/create_site.py` supporting interactive prompts, non-interactive flags for Milestone 18 compatibility, `--from-manifest`, `--dump-manifest`, and `--ai`, plus comprehensive documentation in `documentation/create_site.md` and completion tracking in `milestone_plan.md`.

---

## 2. Quantitative Modularity & Target Budgets

All modified and newly created source files across all 3 milestones must strictly satisfy the project's Modularity Budgets ($\le 350$ lines soft warning, $\le 500$ lines hard ceiling, $\le 12$ methods/class, $\le 40$ lines/function):

| Target File | Current Lines | Planned Net Lines | Budget Status | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `erp/plugin.py` | 96L | ~98L | **PASS** (< 350L) | Declare `dependencies = ["crm"]` on `ERPPlugin` |
| `intelligent_tracker_hub/plugin.py` | 40L | ~42L | **PASS** (< 350L) | Declare `dependencies = ["crm", "video_gallery", "rest_api"]` |
| `home/services.py` | 66L | ~95L ($\le 40$L/fn) | **PASS** (< 350L) | Guard optional `crm`/`todo` integration via `apps.is_installed()` |
| `cms/blocks.py` | 90L | ~110L ($\le 40$L/fn) | **PASS** (< 350L) | Guard optional `erp`, `polls`, and `video_gallery` block imports |
| `plugin_registry/scaffolding/__init__.py` | 0L (New) | ~20L | **PASS** (< 350L) | Package exports for `SiteManifest`, resolver, and AI advisor |
| `plugin_registry/scaffolding/manifest.py` | 0L (New) | ~210L ($\le 12$M, $\le 40$L/fn) | **PASS** (< 350L) | `SiteManifest` dataclass, validation, JSON manifest IO, dependency closure |
| `plugin_registry/scaffolding/ai_advisor.py` | 0L (New) | ~160L ($\le 40$L/fn) | **PASS** (< 350L) | Optional `--ai` Gemini blueprint advisor + deterministic heuristic fallback |
| `plugin_registry/scaffolding/renderers.py` | 0L (New) | ~240L ($\le 40$L/fn) | **PASS** (< 350L) | Split-settings, URLconf, `.env.example`, `requirements.txt`, Docker renderers |
| `plugin_registry/scaffolding/generator.py` | 0L (New) | ~220L ($\le 12$M, $\le 40$L/fn) | **PASS** (< 350L) | `ProjectGenerator` tree copy, package renaming, manifest output, i18n hook |
| `plugin_registry/management/commands/create_site.py` | 0L (New) | ~230L ($\le 12$M, $\le 40$L/fn) | **PASS** (< 350L) | Interactive/non-interactive CLI wizard (`--from-manifest`, `--dump-manifest`, `--ai`) |
| `tests/test_create_site.py` | 0L (New) | ~280L ($\le 40$L/fn) | **PASS** (< 350L) | Unit & E2E scaffolding verification tests |

---

## 3. Surface Invariants & Public API Contracts

1. **Backwards-Compatible Parent Repo Behavior**:
   - In the root `enterprise_website` repository (where all optional apps are installed), `CMSStreamBlock` must expose the exact 7 blocks (`hero`, `richtext`, `features`, `cta`, `video_gallery`, `poll`, `product_showcase`) without migration drift, and `home.services.ingest_website_contact_submission()` must preserve its exact return signature `(contact, lead, interaction, followup_todo)`.
2. **Valid Python Package Identifier Contract**:
   - `SiteManifest.project_name` must match `^[a-z][a-z0-9_]*$` and reject Python keywords or shadowed standard/Django module names (`django`, `site`, `test`, `sys`, `os`, `enterprise_website`).
3. **Transitive `AppPlugin` Dependency Closure Invariant**:
   - Selecting `erp` automatically enables `crm`; selecting `intelligent_tracker_hub` automatically enables `crm`, `video_gallery`, and `rest_api`; selecting `webprogram` sets `enable_labs=True`.
4. **Zero Hardcoded Secrets / Endpoints & Binary Write Invariant**:
   - `ai_advisor.py` must resolve API keys and optional custom endpoints exclusively from environment variables without hardcoded keys or localhost fallbacks; all generated/manifest writes must use UTF-8 binary writes (`write_bytes(content.encode("utf-8"))`) to avoid Windows `\r\r\n` corruption.
5. **Milestone 18 CLI Non-Interactive Readiness**:
   - `SiteManifest` + `create_site` must operate identically via JSON manifest (`--from-manifest`), CLI flags (`--no-input`), or interactive terminal prompts.

---

## 4. Scenario Combinations Matrix

| Scenario ID | Milestone | Subsystem Under Test | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-1701** | Milestone 1 | `SiteManifest` validation, JSON round-trip, transitive `AppPlugin` dependency resolution & optional-app guards | `pytest tests/test_create_site.py tests/test_plugin_registry.py tests/test_home.py tests/test_cms.py` | 100% pass; `erp` pulls `crm`, `intelligent_tracker_hub` pulls `crm`+`video_gallery`+`rest_api`, optional guards never raise `ImportError` |
| **SC-1702** | Milestone 1 | Optional `--ai` Blueprint Advisor (env API parse + offline deterministic keyword fallback) | `pytest tests/test_create_site.py -k ai_advisor` | 100% pass; parses mocked Gemini JSON response cleanly and falls back deterministically when offline/unconfigured |
| **SC-1703** | Milestone 2 | `ProjectGenerator` & `renderers.py` standalone minimal & full Django project generation | `pytest tests/test_create_site.py -k generator` | 100% pass; generated projects in `TemporaryDirectory` pass `manage.py check` and `migrate` |
| **SC-1704** | Milestone 3 | `manage.py create_site` CLI (`--no-input`, interactive prompts, `--from-manifest`, `--dump-manifest`, `--ai`) | `pytest tests/test_create_site.py` | 100% pass; all CLI workflows succeed and `documentation/create_site.md` matches live flags |

---

## 5. Multi-Phase Roadmap & Milestones

### Milestone 1: Composable `SiteManifest` Contract, Plugin Dependency Resolver, AI Blueprint Advisor & Cross-App Optionality Guards
- [x] **erp/plugin.py, intelligent_tracker_hub/plugin.py, home/services.py & cms/blocks.py**: Declare explicit AppPlugin dependencies (erp -> crm; intelligent_tracker_hub -> crm, video_gallery, rest_api) and add graceful optional-app import/installed guards in home/services.py and cms/blocks.py.
- [x] **plugin_registry/scaffolding/__init__.py & plugin_registry/scaffolding/manifest.py**: Implement SiteManifest dataclass, validation rules, JSON manifest export/import (--from-manifest / --dump-manifest support), core vs. optional plugin catalog, and transitive AppPlugin dependency resolver.
- [x] **plugin_registry/scaffolding/ai_advisor.py**: Implement optional --ai blueprint advisor querying Gemini/OpenAI via environment variables with deterministic offline keyword heuristic fallback.
- [x] **tests/test_create_site.py**: Add unit tests for SiteManifest validation, JSON serialization round-trips, transitive plugin dependency resolution, AI advisor parsing/fallback, and optional-app graceful guards.
- [x] **CHANGELOG.md**: Record Milestone 1 completion via python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add.

### Milestone 2: Project Scaffolding Generator Engine (`renderers.py` & `generator.py`)
- [x] **plugin_registry/scaffolding/renderers.py**: Implement modular config renderers for split settings (apps.py, base.py, storage.py, integrations.py, unfold_config.py), urls.py, rest_api/v1_urls.py, .env.example, requirements.txt, and docker-compose.yml.
- [x] **plugin_registry/scaffolding/generator.py**: Implement ProjectGenerator to copy core + selected app trees, rename project package references to project_name, write site_manifest.json, and optionally run i18n bootstrap.
- [x] **tests/test_create_site.py**: Add isolated TemporaryDirectory scaffolding tests verifying generated minimal and full projects pass manage.py check and migrate.
- [x] **CHANGELOG.md**: Record Milestone 2 completion via python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add.

### Milestone 3: `manage.py create_site` Interactive & Non-Interactive CLI Wizard & Documentation (**DEFERRED TO NEXT TURN / MILESTONE**)
- [ ] **plugin_registry/management/commands/create_site.py**: Implement manage.py create_site command supporting interactive wizard prompts, non-interactive CLI flags, --from-manifest, --dump-manifest, and --ai advisor.
- [ ] **documentation/create_site.md & milestone_plan.md**: Write complete create_site wizard documentation with CLI recipes and Scenario Combinations Matrix, and mark Milestone 17 complete in milestone_plan.md.
- [ ] **tests/test_create_site.py**: Add end-to-end call_command('create_site') tests for CLI flags, interactive stdin prompts, manifest export/import, and --ai mode.
- [ ] **CHANGELOG.md**: Record Milestone 3 completion via python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add.
