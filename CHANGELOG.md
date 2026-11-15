# Changelog

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

## [Milestone 1] - AI Rules & Standardization Setup
- **Date:** 2026-10-20
- **Status:** **COMPLETE**
- **Objectives:**
  - Establish workspace and global AI guidelines for comment preservation, persistent task logging, milestone review workflow, and security standards.
- **Files Created / Modified:**
  - `AGENTS.md`: Workspace root guidelines.
  - `.agents/rules/comment_preservation.md`: Reference preservation rules.
  - `.agents/rules/task_logging.md`: Persistent task/migration log rules.
  - `.agents/rules/milestone_workflow.md`: Milestone review protocol.
  - `.agents/rules/security_and_standards.md`: OWASP and cross-platform standards.
  - `documentation/GLOBAL_AI_RULES.md`: Ready-to-copy standard rule for `~/.gemini/config/rules/` and other migration projects.
  - `MIGRATION_LOG.md`: Initialized persistent task tracking log.
- **Verification:**
  - Files created in standard `.agents/rules` and root `AGENTS.md` format.

---

## [Milestone 2] - Navigation & Page Routes Modernization
- **Date:** 2026-10-20
- **Status:** **COMPLETE**
- **Objectives:**
  - Fix broken navigation links in `templates/base.html` that previously pointed to static `about.html`, `services.html`, `products.html`, `contact.html`.
  - Implement Class-Based Views and responsive templates in `home` app for About Us, Services, Products, and Contact.
  - Add routes supporting both standard URLs (`/about/`) and legacy paths (`/about.html`, etc.) for seamless backwards compatibility.
  - Add an "Apps" dropdown in the navbar linking directly to the interactive modules:
    - Todo (`/todo/`)
    - Polls (`/polls/`)
    - Brython WebProgram (`/webprogram/`)
    - REST API (`/rest_api/`)
    - Django Admin (`/admin/`)
  - Update brand logo link to dynamic `{% url 'home:index' %}`.
  - Update `home/templates/home/index.html` buttons and footer links to route to active Django views.

## [Milestone 3] - Logic Fixes, Auth Modernization & Security Hardening
- **Date:** 2026-10-20
- **Status:** **COMPLETE**
- **Objectives:**
  - Fix `user_management/views.py`:
    - Fixed base64 encoding/decoding compatibility for Django 3+ / 5.x in `send_account_activation_email` and `activate_user_account`.
    - Fixed activation template path to `emails/user_management/activation.html`.
    - Corrected broken reverse namespaces (`app:activate_user_account` -> `user_management:activate_user_account`, `hr:user_profile` -> `user_management:profile`).
    - Handled Django 5 `LogoutView` POST-by-default requirement gracefully with `http_method_names = ['get', 'post', 'options']` while adding a secure CSRF POST logout form in the navbar.
    - Updated `SiteUserProfileView` and `SiteUserUpdateView` with `LoginRequiredMixin` and `get_object()` returning `request.user` so `/accounts/profile/` functions without requiring a PK in the URL.
    - Created `user_management/templates/user_management/profile.html`, `logout.html`, and `siteuser_list.html`.
  - Fix `todo/views.py` and templates:
    - Replaced hard-crashing `Todo.objects.get()` with `get_object_or_404(Todo, id=id)`.
    - Sanitized `add` view with empty-title validation and error alerts.
    - Replaced typographical quotes (`”`) with standard double quotes (`"`) in `todo/templates/todo/index.html`.

## [Milestone 4] - Messages Refactoring & Environment Execution Standards
- **Date:** 2026-10-20
- **Status:** **COMPLETE**
- **Objectives:**
  - Refactor `templates/partials/messages.html`:
    - Remove hardcoded test alerts and restore dynamic Django message rendering loop (`{% if messages %} ... {% endif %}`).
    - Eliminate hacky `!important`, full-screen viewport taking `min-height: 100vh`, and intrusive high z-index overlay.
    - Implement clean Bootstrap alerts with gentle drop shadow, dismiss button, and 6-second auto-dismiss.
  - Document Environment & Execution Standards:
    - Eliminate command discovery friction by clearly defining the local virtual environment at `python` (and pip at `.\.venv\Scripts\pip.exe`).
    - Explain that global Windows PATH points to an unconfigured Python stub without project packages installed.
    - Clarify authentication architecture: custom user model `user_management.SiteUser`, separation of front-end `/accounts/login/` vs `/admin/login/` (`is_staff=True`), and how to inspect/create default users.
    - Persist these rules across `.agents/rules/environment_and_execution.md` and root `AGENTS.md`.
- **Files Created / Modified:**
  - `templates/partials/messages.html`
  - `.agents/rules/environment_and_execution.md`
  - `AGENTS.md`
  - `MIGRATION_LOG.md`
- **Verification:**
  - Verified `python manage.py check` passes with 0 issues.
  - Confirmed `templates/partials/messages.html` renders only when messages exist and without intrusive CSS overrides.

---
