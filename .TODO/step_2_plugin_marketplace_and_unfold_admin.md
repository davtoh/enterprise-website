# Step 2 Implementation Plan: `AppPlugin v2`, Zone Separation, `django-unfold` Admin & Module Marketplace

**Plan Slug:** `step_2_plugin_marketplace_and_unfold_admin`  
**Parent Master Plan:** `platform_evolution_master_roadmap` (Master Milestone 2)  
**Architecture Reference:** `docs/ARCHITECTURE.md` (Sections 4, 6 & 7)  
**Execution Mode:** 1-Milestone-Per-Turn Execution Gate (`plan_engine.py`)

---

## 1. Executive Summary

This child plan executes **Master Step 2** across 3 atomic, vertically verified milestones:
1. **Milestone 1 (`AppPlugin v2` Contract, Entry-Point Discovery, `PluginState` Model & Runtime Gating)**: Extend `AppPlugin` (`plugin_registry/base.py`) with `zone` (`public`, `staff`, `labs`), `requires_staff`, `requires_auth`, `is_system`, `stream_blocks`, `api_urlpatterns`, and `dashboard_widgets`. Add external package discovery via `importlib.metadata.entry_points(group="enterprise_website.plugins")`. Create the database-backed `PluginState` model (`slug`, `is_enabled`, `config_json`) with cached lookups and `PluginGatingMiddleware` so disabled plugins return `404` and hide menu items/tasks at runtime without mutating `INSTALLED_APPS`.
2. **Milestone 2 (Zone Separation across `crm`, `erp`, `intelligent_tracker_hub`, `task_runner` & `webprogram` Labs Flag)**: Enforce explicit `zone` metadata (`public`, `staff`, `labs`) across all 12 `*/plugin.py` definitions, mark staff workspace plugins (`crm`, `erp`, `intelligent_tracker_hub`, `task_runner`) with `zone = "staff"` and `requires_staff = True`, and isolate `webprogram` in `zone = "labs"` controlled by `settings.ENABLE_LABS_PLUGINS` while refactoring `menu_management/sync.py::sync_plugin_menus` (currently 111L) into modular helpers ($\le 40$L per function).
3. **Milestone 3 (`django-unfold` Admin Workspace & Interactive Module Marketplace UI)**: Install and configure `django-unfold` in `requirements/base.txt` and `enterprise_website/settings/` (`['daphne', 'unfold', 'django.contrib.admin', ...]`) with grouped sidebar navigation (`CRM`, `ERP`, `Security Hub`, `Platform`, `CMS`), cross-links to `/cms/` and `/rosetta/`, and an interactive **Module Marketplace** admin view (`/admin/marketplace/`) with card grid, zone badges, and live enable/disable toggles backed by `PluginState`.

---

## 2. Quantitative Modularity & Target Budgets

| Target File | Current Lines | Planned Net Lines | Budget Status | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `plugin_registry/base.py` | 63L | ~115L | **PASS** (< 350L) | `PluginZone`, `MenuItemDefinition`, and `AppPlugin v2` contract |
| `plugin_registry/models.py` | 0L (New) | ~75L | **PASS** (< 350L) | `PluginState` model & cache-invalidating save/delete hooks |
| `plugin_registry/registry.py` | 79L | ~160L | **PASS** (< 350L) | Autodiscovery, `entry_points`, `is_plugin_enabled`, enabled-filtered getters |
| `plugin_registry/middleware.py` | 0L (New) | ~55L | **PASS** (< 350L) | `PluginGatingMiddleware` returning `404` for disabled/gated plugin prefixes |
| `plugin_registry/admin_views.py` | 0L (New) | ~110L | **PASS** (< 350L) | Staff-only Module Marketplace card grid & toggle POST handler ($\le 40$L/fn) |
| `menu_management/sync.py` | 119L | ~125L | **PASS** (< 350L) | Decompose 111L `sync_plugin_menus` into $\le 40$L helpers & respect plugin zones |
| `menu_management/context_processors.py` | 59L | ~75L | **PASS** (< 350L) | Filter `get_menu_tree` items by `registry.is_plugin_enabled(item.plugin_source)` |
| `enterprise_website/settings/unfold_config.py` | 0L (New) | ~120L | **PASS** (< 350L) | `UNFOLD` sidebar groups, links to `/cms/`, `/rosetta/`, `/admin/marketplace/` |

---

## 3. Surface Invariants & Public API Contracts

1. **Backwards-Compatible `AppPlugin` & Menu Sync (`tests/test_plugin_registry.py`)**:
   - All 8 existing tests in `tests/test_plugin_registry.py` (`test_registry_autodiscover`, `test_get_plugin_by_name`, `test_sync_plugin_menus_creates_hierarchy`, `test_sync_plugin_menus_is_idempotent`, `test_menu_item_get_url_resolution`, `test_menu_item_visibility_permissions`, `test_sync_menus_management_command`, `test_dynamic_menu_context_processor`) must pass 100%.
2. **Safe Runtime Marketplace Gating Invariant**:
   - Toggling a non-system plugin to `is_enabled=False` in `PluginState` immediately returns HTTP `404` on its `url_prefix` routes via `PluginGatingMiddleware`, hides its menu items in `get_menu_tree()`, and excludes its tasks/templates from `registry.get_all_tasks()` / `registry.get_all_plugin_templates()` without modifying `settings.INSTALLED_APPS` or dropping tables.
   - Core system plugins (`is_system=True`: `home`, `theme_management`, `language_management`) cannot be disabled via the Marketplace UI.
3. **Zone Separation & Labs Feature Flag (`ENABLE_LABS_PLUGINS`)**:
   - `CRMPlugin`, `ERPPlugin`, `IntelligentTrackerPlugin`, and `TaskRunnerPlugin` declare `zone = "staff"` and `requires_staff = True` (restricting navbar visibility in `get_menu_tree` to `user.is_staff=True` while preserving existing view-level `/accounts/login/` redirect behavior).
   - `WebprogramPlugin` declares `zone = "labs"`. When `settings.ENABLE_LABS_PLUGINS` is `False` (and not explicitly overridden in `PluginState`), `registry.is_plugin_enabled("webprogram")` evaluates to `False`, gating `/webprogram/` with HTTP `404` and hiding it from `get_menu_tree()`.
4. **`django-unfold` Admin & Marketplace Compatibility**:
   - `/admin/login/` (`is_staff=True`), all existing `admin.site` model registrations, and `task_runner`'s custom `launch-script/` admin route continue functioning without template or URL regression.
   - `/admin/marketplace/` renders the Module Marketplace card grid for staff users and allows toggling plugins via CSRF-protected POST requests.

---

## 4. Scenario Combinations Matrix

| Scenario ID | Milestone | Focus Area | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-201** | Milestone 1 | `AppPlugin v2`, `PluginState`, Entry Points & Runtime `404` Gating | `pytest tests/test_plugin_registry.py` | 100% pass; disabling plugin in `PluginState` gates route (`404`), menu tree, and tasks |
| **SC-202** | Milestone 2 | Zone Separation (`public`/`staff`/`labs`), `ENABLE_LABS_PLUGINS` & Modular `sync_plugin_menus` | `pytest tests/test_plugin_registry.py tests/test_webprogram.py tests/crm/ tests/erp/ tests/test_intelligent_tracker_hub.py` | 100% pass; `ENABLE_LABS_PLUGINS=False` gates `/webprogram/`; staff plugins hidden from non-staff nav |
| **SC-203** | Milestone 3 | `django-unfold` `/admin/` Integration & Module Marketplace UI | `pytest tests/test_plugin_registry.py tests/test_task_runner.py tests/test_user_management.py` | `/admin/` & `/admin/marketplace/` render `200` for staff; POST toggle updates `PluginState` |
| **SC-204** | All | Modularity Budget Audit & Full Suite | `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" audit --path plugin_registry menu_management enterprise_website/settings --max-lines 350 --max-fn-lines 40` | 0 budget violations; all functions $\le 40$L and files $\le 350$L |

---

## 5. Multi-Phase Roadmap & Milestones

### Milestone 1: `AppPlugin v2` Contract, Entry-Point Discovery, `PluginState` Model & Runtime Gating
- [x] **plugin_registry/base.py**: Add `PluginZone` (`PUBLIC`, `STAFF`, `LABS`) and extend `AppPlugin` with `zone`, `requires_staff`, `requires_auth`, `is_system`, `stream_blocks`, `api_urlpatterns`, `dashboard_widgets`, and their `@classmethod` getters.
- [x] **plugin_registry/models.py & plugin_registry/migrations/0001_initial.py**: Create `PluginState` (`slug`, `is_enabled`, `config_json`, `updated_at`) with cache invalidation on save/delete and generate the initial migration.
- [x] **plugin_registry/registry.py**: Add `importlib.metadata.entry_points(group="enterprise_website.plugins")` discovery in `autodiscover()`, implement `is_plugin_enabled(slug)` and `get_enabled_plugins()`, and filter `get_all_tasks()`, `get_all_plugin_templates()`, `get_all_stream_blocks()`, and `get_all_api_urlpatterns()` by enabled status.
- [x] **plugin_registry/middleware.py, menu_management/context_processors.py & enterprise_website/settings/base.py**: Add `PluginGatingMiddleware` (raising `Http404` when a request matches a disabled plugin's `url_prefix`), wire it into `MIDDLEWARE`, and filter `get_menu_tree()` by `registry.is_plugin_enabled(item.plugin_source)`.
- [x] **tests/test_plugin_registry.py**: Add unit and integration tests for `AppPlugin v2` attributes, `entry_points` discovery, `PluginState` toggle persistence, runtime `404` route gating, and menu/task filtering.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 2: Zone Separation (`Public`, `Staff`, `Labs`), `ENABLE_LABS_PLUGINS` & `sync_plugin_menus` Refactoring
- [x] **crm/plugin.py, erp/plugin.py, intelligent_tracker_hub/plugin.py, task_runner/plugin.py**: Set `zone = "staff"`, `requires_staff = True`, and `requires_auth = True` on staff workspace plugins and propagate `requires_staff` to their `MenuItemDefinition` entries.
- [x] **webprogram/plugin.py, home/plugin.py, theme_management/plugin.py, language_management/plugin.py & enterprise_website/settings/base.py**: Set `zone = "labs"` on `WebprogramPlugin`, mark core plugins (`home`, `theme_management`, `language_management`) with `is_system = True`, and add `ENABLE_LABS_PLUGINS` env-backed setting support in `is_plugin_enabled()`.
- [x] **menu_management/sync.py**: Decompose the 111-line `sync_plugin_menus` function into focused helpers ($\le 40$ lines each) that propagate plugin-level `requires_staff` / `requires_auth` defaults to synced `MenuItem` records.
- [x] **tests/test_plugin_registry.py & tests/test_webprogram.py**: Add tests verifying staff-only menu visibility for `crm`/`erp`/`intelligent_tracker_hub`, `ENABLE_LABS_PLUGINS=False` route `404` and menu hiding for `webprogram`, and `is_system=True` protection.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 3: `django-unfold` Admin Workspace & Interactive Module Marketplace UI (**DEFERRED TO NEXT TURN / MILESTONE**)
- [ ] **requirements/base.txt & enterprise_website/settings/apps.py & enterprise_website/settings/unfold_config.py**: Install `django-unfold`, add `'unfold'` before `'django.contrib.admin'` in `DJANGO_CORE_APPS`, and configure `UNFOLD` sidebar navigation (`CRM`, `ERP`, `Security Hub`, `Platform`, `CMS`) with cross-links to `/cms/`, `/rosetta/`, and `/admin/marketplace/`.
- [ ] **plugin_registry/admin.py, plugin_registry/admin_views.py & enterprise_website/urls.py**: Register `PluginStateAdmin` and mount the staff-only `PluginMarketplaceView` (`/admin/marketplace/`) supporting GET card grid filtering by zone/category and POST enable/disable toggling (blocking `is_system=True` disable attempts).
- [ ] **plugin_registry/templates/plugin_registry/admin_marketplace.html**: Build the responsive Module Marketplace template displaying plugin cards, version/author metadata, zone/status badges, and CSRF-protected toggle forms without inline styles or `!important`.
- [ ] **tests/test_plugin_registry.py**: Add integration tests verifying `/admin/` Unfold rendering, `/admin/marketplace/` staff access control, POST toggling of `PluginState`, and system-plugin disable protection.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.
