# Changelog

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

## [2026-11-15] feat: Home Contact-to-CRM Lead & Follow-Up Intake Pipeline
- **Type**: feat
- **Summary**: Added home/services.py atomic CRM/Todo contact ingestion, wired ContactView.post, pruned unused imports, and expanded tests/test_home.py.
- **Files** (4):
  - `home/models.py`
  - `home/views.py`
  - `tests/test_home.py`
  - `home/services.py`
- **Verification**: pytest tests/test_home.py tests/crm/

## [2026-11-15] fix: Step 1 Milestone 2: Dead-Code Pruning, i18n Fixes & URL Namespace Standardization
- **Type**: fix
- **Summary**: Removed dead upload_pic and index2 views, wrapped webprogram title in gettext_lazy, added timezone_management app_name with root alias fallback, extracted show_results to polls/templatetags/poll_tags.py, and pruned unused imports.
- **Files** (11):
  - `custom_tags/templatetags/present.py`
  - `enterprise_website/urls.py`
  - `language_management/views.py`
  - `tests/test_polls.py`
  - `tests/test_timezone_management.py`
  - `tests/test_webprogram.py`
  - `timezone_management/templates/timezone_management/select.html`
  - `timezone_management/urls.py`
  - ... (+3 more)
- **Verification**: pytest tests/test_polls.py tests/test_timezone_management.py tests/test_webprogram.py tests/test_user_management.py

## [2026-11-15] fix: Step 1 Milestone 1: REST API Permission Lockdown, Serializer Separation & Secret Hygiene
- **Type**: fix
- **Summary**: Extracted UserSerializer and UserViewSet from rest_api/urls.py, enforced IsAuthenticated with staff/self queryset scoping, removed legacy Google Maps key comment, and pruned unused DRF imports.
- **Files** (6):
  - `enterprise_website/urls.py`
  - `rest_api/urls.py`
  - `rest_api/views.py`
  - `templates/partials/scripts.html`
  - `tests/test_rest_api.py`
  - `rest_api/serializers.py`
- **Verification**: python -m pytest tests/test_rest_api.py

## [2026-11-12] feat: Coordinated Framework Upgrade - Django 5.2 LTS, DRF 3.18.2 & Allauth 65.22.0
- **Type**: feat
- **Summary**: Synchronized upgrade of Django 5.2.19, DRF 3.18.2, and Allauth 65.22.0 with allauth settings modernization, DB migrations, assertQuerySetEqual fixes, and Dependabot grouping rules.
- **Files** (3):
  - `MIGRATION_LOG.md`
  - `polls/tests.py`
  - `CHANGELOG.md`
- **Verification**: pytest (381 passed)
