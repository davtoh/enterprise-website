# Step 3 Implementation Plan: Wagtail Hybrid CMS, Blog Engine, `wagtail-localize` & 3-Level Cached Navigation

**Plan Slug:** `step_3_wagtail_cms_blog_and_navigation`  
**Parent Master Plan:** `platform_evolution_master_roadmap` (Master Milestone 3)  
**Architecture Reference:** `docs/ARCHITECTURE.md` (Sections 4, 6 & 7)  
**Execution Mode:** 1-Milestone-Per-Turn Execution Gate (`plan_engine.py`)

---

## 1. Executive Summary

This child plan executes **Master Step 3** across 3 cohesive, vertically verified milestones:
1. **Milestone 1 (Wagtail & `wagtail-localize` Core Setup, `cms` App Models & Theme-Aware `StreamField` Blocks)**: Install and configure `wagtail` and `wagtail-localize` in `requirements/base.txt`, `enterprise_website/settings/apps.py`, `enterprise_website/settings/base.py`, and `enterprise_website/urls.py` (`/cms/` editorial UI, `/documents/`, and catch-all page serving). Create the `cms` app (`StandardPage`, `BlogIndexPage`, `BlogPage`, `BlogCategory`) and reusable, theme-aware `StreamField` blocks (`HeroBlock`, `RichTextSectionBlock`, `FeatureGridBlock`, `CallToActionBlock`) extending `base.html` and `theme-adapter.css` with zero inline styles and zero `!important`.
2. **Milestone 2 (`cms/bridge.py`, 3-Level Menu Hierarchy & Per-Role/Locale Cached Navigation)**: Link Wagtail `show_in_menus=True` page trees (up to 3 levels deep) idempotently into `menu_management.MenuItem` via `cms/bridge.py` and `menu_management/sync.py`. Add versioned per-role/per-locale menu tree caching (`menu_management/cache.py`) with automatic signal-driven invalidation (`cms/signals.py`) on `MenuItem`, `PluginState`, and Wagtail `page_published`/`page_unpublished` events, plus localized Wagtail page title/URL resolution per active locale.
3. **Milestone 3 (3-Level Theme Headers, Contextual Section Sidebar & Seeded `home` CMS Migration)**: Upgrade `bootstrap5`, `tailwind`, and `minimal` header partials (`templates/themes/*/partials/header.html`) to support clickable parent tabs alongside split dropdown toggles, 2-level header dropdowns, and a 3rd-level contextual section sidebar partial (`templates/partials/section_sidebar.html`). Add idempotent initial CMS page & blog seeding (`cms/seed.py` & `seed_cms_pages` command) while preserving 100% backwards compatibility for all legacy `home` routes (`/`, `/about/`, `/about.html`, `/services.html`, `/products.html`, `/contact.html`) and `ContactView` lead intake.

---

## 2. Quantitative Modularity & Target Budgets

| Target File | Current Lines | Planned Net Lines | Budget Status | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `enterprise_website/settings/apps.py` | 56L | ~85L | **PASS** (< 350L) | Register Wagtail, `wagtail-localize`, `modelcluster`, `taggit`, and `cms` |
| `enterprise_website/settings/base.py` | 164L | ~185L | **PASS** (< 350L) | Wagtail i18n/site settings & `RedirectMiddleware` |
| `enterprise_website/urls.py` | 64L | ~85L | **PASS** (< 350L) | Mount `/cms/`, `/documents/`, and Wagtail page catch-all routing |
| `cms/blocks.py` | 0L (New) | ~120L | **PASS** (< 350L) | `HeroBlock`, `RichTextSectionBlock`, `FeatureGridBlock`, `CallToActionBlock` |
| `cms/models.py` | 0L (New) | ~165L | **PASS** (< 350L) | `BlogCategory`, `StandardPage`, `BlogIndexPage`, `BlogPage` ($\le 40$L/fn) |
| `cms/bridge.py` | 0L (New) | ~130L | **PASS** (< 350L) | Idempotent Wagtail `show_in_menus` $\to$ `MenuItem` 3-level tree sync ($\le 40$L/fn) |
| `cms/signals.py` | 0L (New) | ~65L | **PASS** (< 350L) | Signal handlers for Wagtail publish/unpublish & `MenuItem` cache invalidation |
| `cms/seed.py` | 0L (New) | ~140L | **PASS** (< 350L) | Idempotent seeding for root `StandardPage`s, `BlogIndexPage`, and sample `BlogPage` |
| `menu_management/models.py` | 72L | ~95L | **PASS** (< 350L) | Optional `wagtail_page` FK & localized title/URL helper on `MenuItem` |
| `menu_management/cache.py` | 0L (New) | ~70L | **PASS** (< 350L) | Versioned per-role/locale menu tree cache helper & invalidation |
| `menu_management/context_processors.py` | 63L | ~110L | **PASS** (< 350L) | Cached 3-level menu tree builder & active section sidebar context |
| `menu_management/sync.py` | 136L | ~150L | **PASS** (< 350L) | Invoke `cms.bridge.sync_wagtail_menus` and invalidate menu cache |

---

## 3. Surface Invariants & Public API Contracts

1. **Legacy `home` Route & Contact Lead Intake Compatibility (`tests/test_home.py`)**:
   - All 10 named routes in `home/urls.py` (`home:index`, `home:index_file`, `home:about`, `home:about_file`, `home:services`, `home:services_file`, `home:products`, `home:products_file`, `home:contact`, `home:contact_file`) and `ContactView.post` (`crm.Contact` + `crm.Lead` + `todo.Todo` creation) must continue passing 100%.
2. **Multi-Theme & CSS `@layer` Hygiene (`tests/test_theme_management.py`)**:
   - All CMS pages (`StandardPage`, `BlogIndexPage`, `BlogPage`), `StreamField` blocks, updated theme headers (`bootstrap5`, `tailwind`, `minimal`), and the 3rd-level `section_sidebar.html` partial must extend `base.html`, resolve via `ThemeTemplateLoader`, and contain zero `!important` declarations and zero inline `style="..."` attributes.
3. **Unified 3-Level Cached Navigation & `AppPlugin v2` Compatibility (`tests/test_plugin_registry.py`)**:
   - `get_menu_tree()` must cache menu hierarchies per `(menu_slug, auth/staff role, language_code, enabled_plugins)` and invalidate deterministically when any `MenuItem`, `PluginState`, or Wagtail `Page` is saved, deleted, published, or unpublished.
   - Parent menu items with both `children` and a valid landing URL (`url != '#'`) must render a clickable parent link alongside a split dropdown toggle across all 3 themes.
4. **Multilingual CMS Localization (`wagtail-localize`)**:
   - `WAGTAIL_I18N_ENABLED = True` and `WAGTAIL_CONTENT_LANGUAGES` must match `settings.LANGUAGES` (`en`, `es`, `pt`, `fr`, `it`, `ja`), allowing Wagtail pages and `BlogCategory` snippets to be translated across all 6 configured locales.

---

## 4. Scenario Combinations Matrix

| Scenario ID | Milestone | Focus Area | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-301** | Milestone 1 | Wagtail `/cms/`, `StandardPage`, `BlogIndexPage`, `BlogPage`, `StreamField` Blocks & `wagtail-localize` | `pytest tests/test_cms.py tests/test_home.py` | 100% pass; `/cms/login/` resolves; `StandardPage` & `BlogPage` render blocks across all 3 themes & 6 locales |
| **SC-302** | Milestone 2 | `cms/bridge.py` 3-Level Sync, Per-Role/Locale Menu Caching & Signal Invalidation | `pytest tests/test_cms_bridge.py tests/test_plugin_registry.py` | 100% pass; publishing/unpublishing Wagtail pages updates `MenuItem` tree and invalidates cache |
| **SC-303** | Milestone 3 | Clickable Parent Tabs, 2-Level Dropdowns, 3rd-Level Section Sidebar & Seeded CMS Pages | `pytest tests/test_cms.py tests/test_home.py tests/test_theme_management.py tests/test_plugin_registry.py` | 100% pass; all 3 themes render clickable parents, dropdowns, and 3rd-level sidebar with zero `!important` |
| **SC-304** | All | Modularity Budget & Callable Smoke Audit | `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" audit --path cms menu_management home enterprise_website/settings enterprise_website/urls.py --max-lines 350 --max-fn-lines 40` | 0 budget violations; all files $\le 350$L and functions $\le 40$L |

---

## 5. Multi-Phase Roadmap & Milestones

### Milestone 1: Wagtail & `wagtail-localize` Core Setup, `cms` App Models & Theme-Aware `StreamField` Blocks
- [x] **requirements/base.txt, enterprise_website/settings/apps.py, enterprise_website/settings/base.py & enterprise_website/urls.py**: Install `wagtail` and `wagtail-localize`, register Wagtail/localization apps and `cms.apps.CmsConfig`, configure `WAGTAIL_SITE_NAME`, `WAGTAIL_I18N_ENABLED = True`, and `WAGTAIL_CONTENT_LANGUAGES`, and mount `/cms/`, `/documents/`, and Wagtail page serving in `enterprise_website/urls.py`.
- [x] **cms/apps.py, cms/plugin.py, cms/blocks.py & cms/models.py**: Implement `CMSPlugin` (`is_system=True`), theme-aware `StreamField` blocks (`HeroBlock`, `RichTextSectionBlock`, `FeatureGridBlock`, `CallToActionBlock`), and page/snippet models (`BlogCategory`, `StandardPage`, `BlogIndexPage`, `BlogPage`) with migrations.
- [x] **cms/templates/cms/ (`standard_page.html`, `blog_index_page.html`, `blog_page.html`, `blocks/*.html`)**: Create responsive, multi-theme templates extending `base.html` and `theme-adapter.css` with `{% wagtailuserbar %}` and zero inline styles or `!important`.
- [x] **tests/test_cms.py**: Add unit and integration tests for `/cms/` admin routing, `StandardPage`, `BlogIndexPage`, `BlogPage`, `BlogCategory`, `StreamField` block rendering across `bootstrap5`/`tailwind`/`minimal`, and `wagtail-localize` locale translation.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 2: `cms/bridge.py`, 3-Level Menu Hierarchy & Per-Role/Locale Cached Navigation
- [x] **menu_management/models.py & menu_management/migrations/**: Add optional `wagtail_page` ForeignKey on `MenuItem` and helper methods to resolve localized page titles and URLs when linked to a Wagtail `Page`.
- [x] **menu_management/cache.py & menu_management/context_processors.py**: Implement versioned per-role/per-locale menu tree caching (`get_cached_menu_tree`, `invalidate_menu_cache`), 3-level hierarchy construction (`root -> children -> grandchildren`), and active section sidebar tree extraction in `dynamic_menu`.
- [x] **cms/bridge.py, cms/signals.py & menu_management/sync.py**: Implement idempotent `sync_wagtail_menus()` ($\le 40$L per helper) syncing `show_in_menus=True` Wagtail pages into `MenuItem`, call it from `sync_plugin_menus()`, and connect Wagtail `page_published`/`page_unpublished` and `MenuItem`/`PluginState` signals to invalidate the menu cache.
- [x] **tests/test_cms_bridge.py & tests/test_plugin_registry.py**: Add tests verifying 3-level Wagtail page-to-`MenuItem` sync idempotency, localized menu title resolution, cached `get_menu_tree()` hits, and automatic signal invalidation on publish/unpublish/save.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 3: 3-Level Theme Headers, Contextual Section Sidebar & Seeded `home` CMS Migration (**DEFERRED TO NEXT TURN / MILESTONE**)
- [ ] **templates/themes/bootstrap5/partials/header.html, templates/themes/tailwind/partials/header.html & templates/themes/minimal/partials/header.html**: Upgrade all 3 theme headers to render clickable parent tabs with split dropdown toggles when `nav_item.url != '#'`, 2-level dropdown items, and localized dynamic titles without breaking existing `{% trans %}` static labels.
- [ ] **templates/partials/section_sidebar.html & cms/templates/cms/standard_page.html**: Add the 3rd-level contextual section sidebar partial displaying sibling/child pages for deep navigation hierarchies across all 3 themes.
- [ ] **cms/seed.py, cms/management/commands/seed_cms_pages.py & home/views.py**: Implement idempotent `seed_initial_cms_pages()` (seeding `Home`, `About Us`, `Services`, `Products`, `Contact`, `BlogIndexPage`, and a sample `BlogPage` with `StreamField` blocks) and enrich `home/views.py` to expose seeded CMS page content while keeping all legacy `.html` and named routes 100% compatible.
- [ ] **tests/test_cms.py, tests/test_home.py & tests/test_theme_management.py**: Add integration tests verifying clickable parent tabs, 2-level dropdowns, 3rd-level section sidebar rendering, and seeded CMS/Blog pages across `bootstrap5`, `tailwind`, and `minimal`.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.
