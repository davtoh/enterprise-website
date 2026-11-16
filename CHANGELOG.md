# Changelog

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

## [2026-11-15] feat: Step 4 M1: Composable AppPlugin v2 StreamField Blocks & Public/Staff Video Isolation
- **Type**: feat
- **Summary**: Added is_public/requires_staff isolation on VideoGallery/VideoItem, registered VideoGalleryEmbedBlock and PollEmbedBlock via AppPlugin v2 and CMSStreamBlock, and added multi-theme block templates and tests.
- **Files** (16):
  - `cms/blocks.py`
  - `plugin_registry/registry.py`
  - `polls/plugin.py`
  - `tests/test_cms.py`
  - `tests/test_polls.py`
  - `tests/test_video_gallery.py`
  - `video_gallery/admin.py`
  - `video_gallery/models.py`
  - ... (+8 more)
- **Verification**: pytest tests/test_video_gallery.py tests/test_polls.py tests/test_cms.py tests/test_plugin_registry.py

## [2026-11-15] feat: Step 3 Milestone 3: 3-Level Theme Headers, Section Sidebar & Seeded CMS Pages
- **Type**: feat
- **Summary**: Upgraded bootstrap5/tailwind/minimal headers with clickable parent tabs and 2-level dropdowns, added 3rd-level section_sidebar.html, implemented idempotent seed_initial_cms_pages(), and exposed cms_page context in home/views.py.
- **Files** (10):
  - `cms/templates/cms/standard_page.html`
  - `home/views.py`
  - `templates/themes/bootstrap5/partials/header.html`
  - `templates/themes/minimal/partials/header.html`
  - `templates/themes/tailwind/partials/header.html`
  - `tests/test_cms.py`
  - `tests/test_home.py`
  - `cms/management/`
  - ... (+2 more)
- **Verification**: pytest tests/test_cms.py tests/test_home.py tests/test_theme_management.py tests/test_plugin_registry.py

## [2026-11-15] feat: Step 3 Milestone 2: Wagtail Menu Bridge, 3-Level Hierarchy & Per-Role/Locale Cached Navigation
- **Type**: feat
- **Summary**: Added MenuItem.wagtail_page with localized title/URL resolution, 3-level Wagtail-to-MenuItem sync in cms/bridge.py, versioned per-role/locale menu caching in menu_management/cache.py, and signal-driven cache invalidation.
- **Files** (10):
  - `cms/apps.py`
  - `menu_management/context_processors.py`
  - `menu_management/models.py`
  - `menu_management/sync.py`
  - `tests/test_plugin_registry.py`
  - `cms/bridge.py`
  - `cms/signals.py`
  - `menu_management/cache.py`
  - ... (+2 more)
- **Verification**: pytest tests/test_cms_bridge.py tests/test_plugin_registry.py

## [2026-11-15] feat: Step 3 Milestone 1: Wagtail CMS, Blog Models & Theme-Aware StreamField Blocks
- **Type**: feat
- **Summary**: Configured Wagtail 8.1 + wagtail-localize 1.14.5, implemented cms app (CMSPlugin, StandardPage, BlogIndexPage, BlogPage, BlogCategory, StreamField blocks), multi-theme templates, and tests/test_cms.py (23 passed)
- **Files** (7):
  - `.TODO/step_3_wagtail_cms_blog_and_navigation.md`
  - `enterprise_website/settings/apps.py`
  - `enterprise_website/settings/base.py`
  - `enterprise_website/urls.py`
  - `requirements/base.txt`
  - `cms/`
  - `tests/test_cms.py`
- **Verification**: pytest tests/test_cms.py tests/test_home.py

## [2026-11-15] feat: Step 2 Milestone 3: django-unfold Admin Workspace & Module Marketplace UI
- **Type**: feat
- **Summary**: Configured django-unfold admin with grouped sidebar navigation, PluginStateAdmin, and staff-only Module Marketplace (/admin/marketplace/) with zone/category filters and live toggle protection.
- **Files** (9):
  - `enterprise_website/settings/__init__.py`
  - `enterprise_website/settings/apps.py`
  - `enterprise_website/urls.py`
  - `requirements/base.txt`
  - `tests/test_plugin_registry.py`
  - `enterprise_website/settings/unfold_config.py`
  - `plugin_registry/admin.py`
  - `plugin_registry/admin_views.py`
  - ... (+1 more)
- **Verification**: pytest tests/test_plugin_registry.py tests/test_task_runner.py tests/test_user_management.py

## [2026-11-15] feat: Step 2 Milestone 2: Zone Separation, ENABLE_LABS_PLUGINS & sync_plugin_menus Refactoring
- **Type**: feat
- **Summary**: Separated Public/Staff/Labs plugin zones, added ENABLE_LABS_PLUGINS gating, marked core plugins is_system=True, and decomposed sync_plugin_menus into <=40L helpers.
- **Files** (14):
  - `.env.example`
  - `crm/plugin.py`
  - `enterprise_website/settings/base.py`
  - `erp/plugin.py`
  - `home/plugin.py`
  - `intelligent_tracker_hub/plugin.py`
  - `language_management/plugin.py`
  - `menu_management/sync.py`
  - ... (+6 more)
- **Verification**: pytest tests/test_plugin_registry.py tests/test_webprogram.py tests/crm/ tests/erp/ tests/test_intelligent_tracker_hub.py tests/test_task_runner.py tests/test_user_management.py

## [2026-11-15] feat: AppPlugin v2, Entry Points, PluginState & Runtime Gating
- **Type**: feat
- **Summary**: Added PluginZone, AppPlugin v2 extension attributes, entry_points discovery, PluginState with cache invalidation, PluginGatingMiddleware (404 on disabled routes), and menu tree filtering.
- **Files** (10):
  - `.TODO/step_2_plugin_marketplace_and_unfold_admin.md`
  - `enterprise_website/settings/base.py`
  - `menu_management/context_processors.py`
  - `plugin_registry/__init__.py`
  - `plugin_registry/base.py`
  - `plugin_registry/registry.py`
  - `tests/test_plugin_registry.py`
  - `plugin_registry/middleware.py`
  - ... (+2 more)
- **Verification**: pytest tests/test_plugin_registry.py tests/test_webprogram.py tests/crm/ tests/erp/ tests/test_intelligent_tracker_hub.py tests/test_task_runner.py tests/test_user_management.py
