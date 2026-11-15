# Master Roadmap: Enterprise Website Composable Platform & Wagtail CMS Evolution

**Plan Slug:** `platform_evolution_master_roadmap`  
**Architecture Reference:** `docs/ARCHITECTURE.md`  
**Status:** **ACTIVE MASTER PLAN** (5 Master Steps)  
**Execution Mode:** 1-Milestone-Per-Turn Gate (`plan_engine.py`)

---

## 1. Executive Summary & Architectural Objective

Transform `enterprise_website` from 18 siloed Django applications with static marketing views into a **cohesive, multi-theme, admin-driven enterprise platform** built on the 6 architectural decisions locked via `/grill-me` in `docs/ARCHITECTURE.md`:
1. **Wagtail Hybrid CMS (`/cms/`)**: Hierarchical `Page` tree, `StreamField` block composer, Side-by-Side Live Preview, Frontend Userbar, and `BlogIndexPage`/`BlogPage` rendered through `ThemeTemplateLoader` and `theme-adapter.css` (`bootstrap5`, `tailwind`, `minimal`).
2. **Modern Staff Backoffice (`/admin/`)**: `django-unfold` admin workspace cross-linked with `/cms/`, `/rosetta/`, and frontend operational dashboards (`/crm/`, `/erp/`, `/security/`, `/tasks/`).
3. **Unified Navigation & Dynamic i18n**: Idempotent `cms_bridge` syncing Wagtail `show_in_menus` pages into cached `menu_management` (`MenuItem`), clickable parent tabs, 2-level header dropdowns + 3rd-level contextual section sidebars, and `wagtail-localize` across all 6 locales (`en`, `es`, `pt`, `fr`, `it`, `ja`).
4. **Zone Separation & Tool Lifecycle**: Clear boundary between **Public Portal**, **Staff Workspace (`requires_staff=True`)**, and **Labs (`ENABLE_LABS_PLUGINS`)**, promoting `todo` into a cross-app `ActionItem` tracker (`GenericForeignKey`) and isolating `webprogram` behind Labs.
5. **Cross-App Data & Block Reuse (`AppPlugin v2`)**: Contact/CTA forms feeding `crm.Lead` + follow-up `ActionItem`; `erp.Product` powering public catalog pages/blocks; `erp.Invoice` linking to `crm.Company`/`crm.Contact`; `video_gallery` and `polls` exposed as embeddable Wagtail `StreamField` blocks.
6. **Security Hardening, Unified `/api/v1/` & Module Marketplace**: Lock down anonymous PII exposure on `/rest_api/users/`, clean secret fallbacks and dead views, unify REST APIs under `/api/v1/` with `drf-spectacular` OpenAPI 3 docs, and add a database-backed `PluginState` Module Marketplace UI in `/admin/` with Python entry-point discovery.

---

## 2. Quantitative Modularity & Target Budgets

All modified and newly created source files across all 5 steps must strictly obey the project's Modularity Budgets ($\le 350$ lines soft warning, $\le 500$ lines hard ceiling, $\le 12$ methods/class, $\le 40$ lines/function):

| Subsystem / File Target | Baseline Lines | Target Ceiling | Budget Action |
| :--- | :--- | :--- | :--- |
| `rest_api/urls.py`, `views.py`, `serializers.py` | 58L (monolithic `urls.py`) | $\le 120$L each | Split serializers/viewsets out of `urls.py` (Step 1) |
| `home/views.py` & `home/services.py` | 76L | $\le 150$L each | Extract Lead Intake helper; transition static views in Step 3 |
| `plugin_registry/` (`base.py`, `models.py`, `marketplace.py`) | 158L total | $\le 250$L per file | Modularize `AppPlugin v2`, `PluginState`, and entry points (Step 2) |
| `menu_management/` (`models.py`, `sync.py`, `context_processors.py`) | 315L total | $\le 250$L per file | Refactor `sync_plugin_menus` (111L fn $\to \le 40$L helpers) & add cache (Step 3) |
| `cms/` (New Wagtail Page, Blog & StreamField Block app) | 0L (New) | $\le 300$L per file | Separate `models.py`, `blocks.py`, `bridge.py`, `signals.py` (Steps 3–4) |
| `erp/pdf.py` & `intelligent_tracker_hub/api/*.py` | 248L fn / 195L fn | $\le 350$L file / $\le 40$L fn | Decompose oversized functions in Step 5 |

---

## 3. Surface Invariants & Public API Contracts

1. **Auth & User Model Invariant**: `AUTH_USER_MODEL = 'user_management.SiteUser'` (`enterprise_website/settings/security.py`), front-end `/accounts/login/`, Allauth 65.x middleware order, and `/admin/login/` (`is_staff=True`) remain unbroken.
2. **Multi-Theme & CSS `@layer` Invariant**: All CMS pages, blog posts, and `StreamField` blocks must extend `base.html`, resolve via `theme_management.loaders.ThemeTemplateLoader`, and render with zero `!important` and zero horizontal overflow across `bootstrap5`, `tailwind`, and `minimal`.
3. **Edge AI API Contract Invariant**: Existing HMAC-signed endpoints under `/api/v1/security/*`, `/api/v1/cameras/*`, and `/api/v1/gallery/*` (`intelligent_tracker_hub/api_urls.py`) must preserve exact request/response schemas and status codes.
4. **Legacy URL Compatibility Invariant**: Legacy routes (`/about.html`, `/services.html`, `/products.html`, `/contact.html`, `/videos/`) must continue resolving `200`/`302` without broken links.
5. **Safe Runtime Marketplace Gating Invariant**: Toggling a plugin off in `PluginState` must gate routes (`404`), menus, and editor blocks at runtime without mutating `settings.INSTALLED_APPS` or dropping database tables.

---

## 4. Scenario Combinations Matrix

| Scenario ID | Master Step | Subsystem Under Test | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-M01** | Step 1 | Security, REST Auth, Lead Intake & Clean Hygiene | `pytest tests/test_rest_api.py tests/test_home.py tests/test_timezone_management.py tests/test_user_management.py` | 100% pass; anon `/rest_api/users/` rejected (`401`/`403`); contact form creates `crm.Lead` |
| **SC-M02** | Step 2 | `AppPlugin v2`, `PluginState` Marketplace & `django-unfold` | `pytest tests/test_plugin_registry.py` | 100% pass; runtime disable gates plugin routes & menus cleanly |
| **SC-M03** | Step 3 | Wagtail Hybrid CMS, Blog, `wagtail-localize` & 3-Level Cached Menus | `pytest tests/test_home.py tests/test_theme_management.py` | 100% pass; Wagtail pages & blog render across all 3 themes & sync to `menu_management` |
| **SC-M04** | Step 4 | Composable `StreamField` Blocks (`video_gallery`, `polls`, `erp`, `crm`) & `ActionItem` | `pytest tests/test_video_gallery.py tests/test_polls.py tests/test_todo.py tests/crm/ tests/erp/` | 100% pass; blocks render cleanly; `erp.Invoice` links to `crm`; `todo` links via `GenericForeignKey` |
| **SC-M05** | Step 5 | Unified `/api/v1/` (`drf-spectacular`) & Modularity Budget Audit | `pytest` | Full suite passes 100%; `diagnose.py audit` passes $\le 350$L / $\le 40$L fn targets |

---

## 5. Multi-Step Master Roadmap

### Step 1: Security, Dead-Code & Hygiene Hardening + Lead Intake Pipeline (**ACTIVE EXECUTION TARGET**)
- [x] **Child Plan**: `.TODO/step_1_security_hygiene_hardening.md`
- [x] **rest_api/**: Extract `UserSerializer` and `UserViewSet` from `rest_api/urls.py` into `rest_api/serializers.py` and `rest_api/views.py`, enforce `IsAuthenticated` (staff full list, non-staff self-only) on `UserViewSet`, and update `tests/test_rest_api.py` for anonymous rejection + authenticated access.
- [x] **enterprise_website/settings/ & templates/partials/scripts.html**: Remove commented Google Maps API key from `templates/partials/scripts.html`, harden `SECRET_KEY` and `INTELLIGENT_TRACKER_SECRET_KEY` production checks (`DEBUG=False`), and clean unused imports in `enterprise_website/urls.py`.
- [x] **user_management/, webprogram/, language_management/, timezone_management/, polls/**: Remove dead `upload_pic` and `index2` views, wrap `webprogram` title in `gettext_lazy`, remove unused `LayoutLanguages` model/form (or mark deprecated cleanly with migration check), add `app_name = 'timezone_management'` (updating `select.html` and `tests/test_timezone_management.py`), and move `show_results` template tag from `custom_tags` to `polls` (keeping backwards-compatible import shim).
- [x] **home/views.py & home/services.py**: Wire `ContactView.post` to create/update `crm.Contact`, create a `crm.Lead` (`LeadSource.WEBSITE`), and create a follow-up `todo.Todo` item, verified by new tests in `tests/test_home.py`.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Step 2: `AppPlugin v2`, Zone Separation, `django-unfold` Admin & Module Marketplace (**DEFERRED TO NEXT TURN / MILESTONE**)
- **Child Plan**: `.TODO/step_2_plugin_marketplace_and_unfold_admin.md`
- [ ] **plugin_registry/**: Extend `AppPlugin` (`v2`) with `zone` (`public`, `staff`, `labs`), `stream_blocks`, `api_urlpatterns`, `dashboard_widgets`, and `importlib.metadata.entry_points(group="enterprise_website.plugins")` discovery.
- [ ] **plugin_registry/models.py & middleware.py**: Add `PluginState` model (`slug`, `is_enabled`, `config_json`) with cached runtime route/menu/task gating so disabled plugins return `404` and hide menu items without mutating `INSTALLED_APPS`.
- [ ] **enterprise_website/settings/ &plugin_registry/admin_views.py**: Integrate `django-unfold` on `/admin/` with grouped sidebar navigation (`CRM`, `ERP`, `Security Hub`, `Platform`, `CMS`), cross-links to `/cms/` and `/rosetta/`, and an interactive **Module Marketplace** card grid for toggling plugins.
- [ ] **webprogram/ & crm/ & erp/ & intelligent_tracker_hub/**: Enforce zone visibility (`requires_staff=True` on staff workspace plugins; `ENABLE_LABS_PLUGINS` feature flag on `webprogram`) and verify with unit/integration tests.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Step 3: Wagtail Hybrid CMS, Blog Engine, `wagtail-localize` & 3-Level Cached Navigation (**DEFERRED TO NEXT TURN / MILESTONE**)
- **Child Plan**: `.TODO/step_3_wagtail_cms_blog_and_navigation.md`
- [ ] **requirements/base.txt & enterprise_website/settings/**: Install and configure `wagtail` and `wagtail-localize` at `/cms/` alongside existing apps and `LocaleMiddleware`.
- [ ] **cms/ (New App)**: Implement `StandardPage`, `BlogIndexPage`, `BlogPage`, `BlogCategory`, and theme-aware `StreamField` blocks (`HeroBlock`, `RichTextSectionBlock`, `FeatureGridBlock`, `CallToActionBlock`) extending `base.html` and `theme-adapter.css`.
- [ ] **menu_management/ & cms/bridge.py**: Refactor `sync_plugin_menus` into modular helpers ($\le 40$L/fn), link Wagtail `show_in_menus` page trees idempotently into `MenuItem`, and add per-role/locale cache invalidation on `MenuItem` and Wagtail page publish/unpublish signals.
- [ ] **templates/themes/*/partials/header.html**: Upgrade `bootstrap5`, `tailwind`, and `minimal` headers to support clickable parent tabs, 2-level dropdowns, and a 3rd-level contextual section sidebar partial, migrating static `home` pages into seeded Wagtail pages while preserving legacy `.html` route compatibility.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Step 4: Cross-App Composable Blocks, Public ERP Catalog & `ActionItem` Promotion (**DEFERRED TO NEXT TURN / MILESTONE**)
- **Child Plan**: `.TODO/step_4_cross_app_blocks_and_pipelines.md`
- [ ] **video_gallery/ & polls/**: Separate public `VideoGallery` items from staff-only `SecurityEvent` evidence (`is_public` / `requires_staff`) and register embeddable Wagtail `StreamField` blocks (`VideoGalleryEmbedBlock`, `PollEmbedBlock`) via `AppPlugin v2`.
- [ ] **erp/ & crm/**: Add `is_published` public catalog support to `erp.Product` with a reusable `ProductShowcaseBlock`, and add optional `crm_company` / `crm_contact` ForeignKeys on `erp.Invoice` while keeping plain-text customer fields backwards-compatible.
- [ ] **todo/**: Promote `Todo` into a cross-app `ActionItem` model by adding optional `owner` (`SiteUser`), `status`, `due_date`, and `GenericForeignKey` (`content_type`, `object_id`) linking to `crm.Lead`, `erp.Invoice`, and `intelligent_tracker_hub.SecurityEvent` while preserving `plugin_templates` multi-theme overrides.
- [ ] **language_management/ & timezone_management/**: Sync user language and timezone selections to `SiteUser` profile preferences when authenticated.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Step 5: Unified `/api/v1/` (`drf-spectacular`), Ecosystem Ops & Modularity Paydown (**DEFERRED TO NEXT TURN / MILESTONE**)
- **Child Plan**: `.TODO/step_5_unified_api_and_modularity_paydown.md`
- [ ] **rest_api/ & enterprise_website/urls.py**: Integrate `drf-spectacular` (`/api/v1/schema/`, `/api/v1/docs/`), auto-mount `AppPlugin.api_urlpatterns` under `/api/v1/`, and keep `/rest_api/` routing compatible.
- [ ] **crm/ & erp/ & location_management/**: Add `django-filter` and `django-import-export` integration for admin and list views, plus `django-htmx` middleware for partial rendering.
- [ ] **erp/pdf.py & intelligent_tracker_hub/**: Decompose oversized functions (`generate_invoice_pdf`, `access_control.py::post`, `video_evidence.py::post`, `security_events.py::post`, `video_streaming.py::get`) and `intelligent_tracker_hub/templates/intelligent_tracker_hub/dashboard.html` (630L) into partials/helpers under the 350L/40L modularity budget.
- [ ] **tests/ & .diagnostics/**: Run full regression suite (`pytest`), `diagnose.py audit`, `diagnose.py scan --prune`, and final `plan_engine.py digest`.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.
