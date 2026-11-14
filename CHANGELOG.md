# Changelog

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

## [Milestone 5] - Full Application Flash Messaging Integration
- **Date:** 2026-10-20
- **Status:** **COMPLETE**
- **Objectives:**
  - Wire Django messages framework across all critical user interactions:
    - **Login (`user_management.views.LoginView`)**:
      - `form_valid`: Displays `messages.success` greeting the user by name upon successful login.
      - `form_invalid`: Displays `messages.error` ("Invalid username or password. Please check your credentials and try again.").
    - **Logout (`user_management.views.LogoutView`)**:
      - `dispatch`: Displays `messages.info` ("You have been successfully logged out. See you soon!").
    - **Sign Up / Registration (`user_management.views.SignUpView`)**:
      - `form_valid`: Displays `messages.success` notifying account creation and prompting login.
      - `form_invalid`: Displays `messages.error` prompting correction of registration errors.
    - **Account Activation (`user_management.views.activate_user_account`)**:
      - Success: Displays `messages.success` and redirects to profile.

## [Milestone 6] - Internationalization (i18n), Rosetta Mapping & Automated Translation Baseline
- **Date:** 2026-10-21
- **Status:** **COMPLETE**
- **Objectives:**
  - **AI & Project Rule Updates:**
    - Created [`.agents/rules/rosetta_and_i18n.md`](rosetta_and_i18n.md) defining strict i18n and Rosetta standards for all new templates, models, and views.
    - Updated [`AGENTS.md`](AGENTS.md) with **Section 6: Internationalization (i18n) & Rosetta Translation**.
  - **Rosetta & Machine Translation Settings:**
    - Configured `django.template.context_processors.i18n` in `TEMPLATES['OPTIONS']['context_processors']` within `enterprise_website/settings.py`.
    - Enabled `ROSETTA_ENABLE_TRANSLATION_SUGGESTIONS = True` and added optional API keys (`DEEPL_AUTH_KEY`, `OPENAI_API_KEY`, `AZURE_CLIENT_SECRET`, `GOOGLE_APPLICATION_CREDENTIALS_PATH`) in `enterprise_website/settings.py` and `.env.example`.
  - **Comprehensive Codebase Mapping & Translation Tagging:**
    - Mapped and wrapped all untranslated strings across:
      - Core layout: `templates/base.html`, `templates/admin/base_site.html`, `templates/signup.html`, `templates/base_form.html`, `templates/registration/logged_out.html`.
      - Home App: `index.html`, `about.html`, `services.html`, `products.html`, `contact.html`, and contact flash messages in `home/views.py`.
      - User Management App: `login.html`, `logout.html`, `profile.html`, `siteuser_list.html`, `signup.html`, `upload_image_form.html`, password reset templates (`password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`, `password_reset_email.html`), activation email (`activation.html`), `user_management/forms.py` (image validation, birthdate validation, ImageUploadForm label), and all authentication flash messages in `user_management/views.py`.

## [Milestone 7] - Documentation Consolidation & System Operations Manual
- **Date:** 2026-10-21
- **Status:** **COMPLETE**
- **Objectives:**
  - **Single Root README Consolidation:**
    - Consolidated all relevant legacy setup instructions, production MySQL configurations, data fixtures, and project purpose from `README.rst` into `README.md`.
    - Removed redundant root `README.rst` to maintain a single source of truth (`README.md`).
  - **Comprehensive System Manual Creation:**
    - Created [`documentation/README.md`](README.md) detailing:
      - Project executive summary, purpose, and value proposition.
      - Full architectural directory breakdown across all apps (`home`, `user_management`, `todo`, `polls`, `language_management`, `location_management`, `timezone_management`, `rest_api`, `webprogram`, `custom_tags`).
      - Detailed feature descriptions for each module.
      - System workflows with Mermaid diagrams (Authentication lifecycle, i18n & Rosetta translation pipeline, Geo-data ingestion, and Polling/voting).
      - Step-by-step commands guide for virtual environments, migrations, fixtures (`populate_users --test`), location databases (`populate_locations`), and poll management (`closepoll`).
      - Full commands reference for translation tooling (`makemessages`, `auto_translate` with all backend and flag variations, and `compilemessages`).

## [Milestone 8] - Plugin Registry & Dynamic Menus System
- **Date:** 2026-10-22
- **Status:** **COMPLETE**
- **Objectives:**
  - Build `plugin_registry` Django application with `AppPlugin` base interface and `registry.autodiscover()`.
  - Build `menu_management` Django application with `Menu` and `MenuItem` models supporting hierarchy, URL reverse resolution, permission checks, and plugin origin tracking.
  - Create `sync_menus` command and admin action to synchronize discovered `AppPlugin` definitions into active database menus without overriding manual user customizations.
  - Implement `dynamic_menu` context processor injecting structured tree `main_navigation` into all templates.
  - Update `templates/base.html` to render the dynamic navigation menu with graceful static fallback.
  - Register `home`, `todo`, `polls`, `webprogram`, and `rest_api` apps with `plugin.py` implementations.
  - Add `documentation/plugin_system.md` detailing plugin creation and menu management workflows.
- **Files Created / Modified:**
  - `plugin_registry/` (`base.py`, `registry.py`, `apps.py`, `__init__.py`)
  - `menu_management/` (`models.py`, `apps.py`, `admin.py`, `context_processors.py`, `sync.py`, `management/commands/sync_menus.py`, `migrations/0001_initial.py`)
  - `home/plugin.py`, `todo/plugin.py`, `polls/plugin.py`, `webprogram/plugin.py`, `rest_api/plugin.py`
