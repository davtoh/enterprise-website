# Modernization & Production Readiness Audit (TODO & Roadmap)

**Project:** Enterprise Website (Django)  
**Status:** In Progress — Phase 1, 2, 3 & Migration Execution Complete (Django 5.0 on Python 3.12)  
**Primary Goal:** Modernize codebase, ensure cross-platform operability (Linux, macOS, Windows), and establish clean production deployment standards.

---

## 1. Executive Summary & Progress

| Area | Initial Legacy State | Modernized State | Status |
| :--- | :--- | :--- | :--- |
| **Python Version** | Python 3.6/3.7 (EOL) | **Python 3.12.10** | **DONE** |
| **Django Version** | Django 2.0.6 (EOL since 2019) | **Django 5.0.14** | **DONE** |
| **Secrets Handling** | Raw `keys.json` committed with plaintext secrets & passwords | `.env` with `python-dotenv`, secrets excluded in `.gitignore`, `.env.example` template provided | **DONE** |
| **Database Support** | Hardcoded to MySQL via `mysqlclient` (fails if MySQL is not installed locally) | OS-agnostic dynamic `DATABASES`: Default SQLite for 0-setup local run, MySQL/Postgres via `.env` | **DONE** |
| **Timezone Management** | Legacy `django-easy-timezones` with discontinued MaxMind `.dat` | Python 3.12 standard library `zoneinfo` + `tzdata`, graceful signal fallback | **DONE** |
| **Dependencies & Packaging** | Single 44-line `requirements.txt` with legacy comments and unpinned mix | Modular: `requirements/base.txt`, `requirements/local.txt`, `requirements/production.txt` | **DONE** |
| **Django Compatibility Fixes** | `force_text`, invalid escape syntax, `allauth` AccountMiddleware | `force_str`, raw strings in `todo/urls.py` and `utils.py`, `allauth.account.middleware.AccountMiddleware` added | **DONE** |
| **Migrations** | Unapplied migrations | All migrations successfully executed on local database (`python manage.py migrate` OK) | **DONE** |
| **Documentation** | Outdated `README.rst` with syntax errors & Ubuntu-only instructions | Modern `README.md` with cross-platform instructions (Windows PowerShell, Linux/macOS bash) | **DONE** |
| **Containerization** | None | Multi-stage `Dockerfile`, `docker-compose.yml` (PostgreSQL 16, Redis 7, Nginx 1.27), `docker-compose.override.yml` | **DONE** |
| **Production Security** | Zero SSL / HSTS / cookie protections | `check --deploy` clean, HSTS preload, secure cookies, framing protection, proxy SSL headers | **DONE** |
| **CI/CD Automation** | None | GitHub Actions (`.github/workflows/ci.yml`) for tests, coverage upload, and container publishing | **DONE** |
| **Geodata Delivery** | 175MB raw `world.sql` directly on root | `download_geodata` command for streaming download on-demand; kept out of Git | **DONE** |
| **Async Tasks & Worker** | Synchronous only; blocked long operations | Celery 5.6 + Redis 8 + Flower 2.2 + Django Channels WebSocket task progress streaming (`task_runner` app) | **DONE** |

---

## 2. Multi-Platform (OS-Agnostic) Strategy

Identical behavior across **Linux**, **macOS**, and **Windows**:
1. **Zero OS-Branching in Settings:**
   - Removed `DB_USER_WINDOWS`, `DB_USER_LINUX`, `DB_USER_DARWIN`.
   - Replaced with standard 12-Factor app environment variables (`.env`).
2. **Unified Path Management:**
   - All directory anchors use `pathlib.Path` (`BASE_DIR / 'staticfiles'`).
3. **Database Flexibility:**
   - `USE_SQLITE=True` enables instant local development out-of-the-box on any OS without requiring C/C++ compilation tools for `mysqlclient`.
   - Production can switch to `DB_ENGINE=django.db.backends.mysql` or `postgresql` simply via `.env`.

---

## 3. Action Plan & Status Checklist

### Phase 1: Security & Hygiene
- [x] Add `keys.json` and `.env` to `.gitignore`.
- [x] Create `.env.example` with template keys and sensible defaults.
- [x] Isolate and ignore local `.sqlite3` and media files.
- [x] Ensure 175MB `world.sql` and `world.sql.json` stay out of git history; added `download_geodata` on-demand stream command.

### Phase 2: Python & Virtual Environment Setup
- [x] Install Python 3.12 runtime.
- [x] Create isolated `.venv` using Python 3.12.
- [x] Audit requirements and separate into `requirements/base.txt`, `requirements/local.txt`, `requirements/production.txt`.
- [x] Freeze working, tested dependencies into `requirements/base.txt`.

### Phase 3: Django Settings & OS-Agnostic Refactoring
- [x] Replace `custom_tags.management.commands.secret_keys` JSON reading with `python-dotenv`.
- [x] Make `DATABASES` dynamic (SQLite out-of-the-box, configurable MySQL/Postgres in prod).
- [x] Modernize timezone handling using Python 3.12 standard library `zoneinfo`.
- [x] Fix deprecated Django 2.x APIs (`force_text` -> `force_str`, `USE_L10N`, `DEFAULT_AUTO_FIELD`, `allauth.account.middleware.AccountMiddleware`).
- [x] Resolve `SyntaxWarning` invalid escape sequences in `todo/urls.py` and `utils.py`.

### Phase 4: Verification & Migrations
- [x] `python manage.py check` passes with 0 issues.
- [x] `python manage.py showmigrations` and `python manage.py migrate` executed cleanly.
- [x] Run automated test suite (`pytest`: 109 tests passing, 80% statement coverage report in `htmlcov/`).

### Phase 5: Production Readiness & Containerization
- [x] Add cross-platform `README.md` (Windows, Linux, macOS).
- [x] Add multi-stage `Dockerfile` (builder + slim runtime with non-root appuser) and `docker-compose.yml` (web, db, redis, nginx).
- [x] Add `docker-compose.override.yml` for local dev (SQLite mode, live reload) and `.dockerignore`.
- [x] Configure production security headers (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS, nosniff, `X_FRAME_OPTIONS = 'DENY'`).
- [x] Add GitHub Actions CI/CD pipeline (`.github/workflows/ci.yml`) for automated check, deploy check, pytest, coverage, and Docker registry publish.

### Phase 6: Routing, AI Standards & Logic Modernization
- [x] AI Governance: Root `AGENTS.md`, modular `.agents/rules/`, and portable `documentation/GLOBAL_AI_RULES.md` for comment retention, persistent logging, and milestone reviews.
- [x] Persistent Logging: Initialized and actively maintained `MIGRATION_LOG.md`.
- [x] Navigation & Routes: Fixed navbar broken links (`about.html`, `services.html`, etc.) to dynamic Django routes (`home:index`, `home:about`, `home:services`, `home:products`, `home:contact`).
- [x] Content Pages: Built responsive CBVs and templates for About Us, Services, Products, and Contact with backwards-compatible `.html` URL aliases.
- [x] Interactive Modules Menu: Added "Apps" dropdown to navbar linking directly to Todo, Polls, Brython, REST API, and Admin.
- [x] User Management & Auth: Fixed Django 5 LogoutView GET/POST support, base64 encoding/decoding, reverse URLs, and created missing templates (`profile.html`, `logout.html`, `siteuser_list.html`).
- [x] Todo & Polls Logic: Replaced hard lookups with `get_object_or_404()`, fixed typographical curly quotes in templates, and enhanced card styling while preserving all original learning references.

### Phase 7: Automated Testing & Code Quality (Milestone 9)
- [x] Configured `pytest-django` via `pytest.ini` and `coverage` via `.coveragerc`.
- [x] Comprehensive test suites covering all applications:
  - `tests/test_home.py` (13 tests) — 5 public pages (standard + `.html`), contact form submission & validation.
  - `tests/test_user_management.py` (17 tests) — signup, login, logout, profile update, activation token flow, AJAX endpoints, commands (`populate_users`), form validators, and model representations.
  - `tests/test_todo.py` (11 tests) — list views, authenticated greetings, add, detail with timezone diagnostics, delete, and 404 handling.
  - `tests/test_polls.py` (15 tests) — published/future questions, detail view, voting with concurrency expression (`F('votes') + 1`), error redisplay, results, and `closepoll` command.
  - `tests/test_language_management.py` (11 tests) — language switcher (`/i18n/setlang/`), placeholder preservation engine, and `auto_translate` backends.
  - `tests/test_timezone_management.py` (4 tests) — `TimezoneMiddleware` activation/deactivation and `set_timezone` view.
  - `tests/test_plugin_registry.py` (8 tests) — plugin autodiscovery, menu auto-population, `sync_menus` command, URL resolution, and permission filters.
  - `tests/test_rest_api.py` (5 tests) — DRF root, paginated users list, user details, and dynamic query filtering (`?val=username&val=email`).
  - `tests/test_webprogram.py` (2 tests) — Brython WebProgram views.
  - `tests/test_utils_and_extra.py` (9 tests) — referer parser and avatar image validator edge cases.
- [x] Codebase stabilization fixes:
  - Fixed `activate_user_account` URL parameter naming (`uidb64`/`token` vs `slug`/`slug2`) and added backward-compatible fallback kwargs.
  - Fixed `TimezoneMiddleware` and `timezone_management/views.py` `ModuleNotFoundError: pytz` by implementing standard library `zoneinfo` fallbacks.
  - Modernized `polls/tests.py` `assertQuerysetEqual` calls for Django 5.
  - Fixed string format specifiers in avatar validation (`%(w)d x %(h)d` and `{max_size}k`).
  - Added ordering to `UserViewSet` queryset to eliminate DRF pagination warnings.
- [x] Verification: 106 tests passing, 80% statement coverage achieved with HTML report in `htmlcov/`.

---

## 4. Milestone 11 — Celery & Async Background Task Infrastructure
- [x] Celery and Broker Configuration:
  - Installed `celery>=5.3.6`, `redis>=5.0.0`, and `flower>=2.0.1` in `requirements/base.txt`.
  - Configured `enterprise_website/celery.py` and linked Celery app in `enterprise_website/__init__.py`.
  - Added Celery broker, result backend, timezone, serialization, and eager execution settings to `enterprise_website/settings.py`.
- [x] Created `task_runner` Application:
  - `TaskJob` model (`task_runner/models.py`) with lifecycle states (`PENDING`, `RUNNING`, `SUCCESS`, `FAILURE`, `REVOKED`), progress percentage tracking, live log output, error messages, and Channel layer broadcasting.
  - `TrackedTask` base class (`task_runner/base.py`) providing automatic task lifecycle management, exception logging, and incremental progress helper `self.update_job_progress()`.
  - `TaskProgressConsumer` (`task_runner/consumers.py`) streaming live task snapshots and incremental broadcasts to browsers via Django Channels WebSockets (`ws/tasks/<task_id>/`).
  - Reusable template tag `{% task_progress_widget task_id %}` (`task_runner/templatetags/task_runner_tags.py`) with real-time animated progress bar, status badges, live auto-scrolling terminal console, and WebSocket connection with HTTP polling fallback.
  - Staff management views (`task_runner/views.py` and `task_runner/urls.py`): `/tasks/` (dashboard with filters/search), `/tasks/<task_id>/` (detail view with widget), `/tasks/<task_id>/status/` (JSON API), and `/tasks/trigger/` (task queue launcher).
  - Django Admin integration (`task_runner/admin.py`) embedding the live real-time widget in task change forms and providing admin actions.
- [x] Background Task Implementations:
  - `run_auto_translate` (`task_runner.tasks.run_auto_translate`): asynchronous catalog translation streaming progress and log lines.
  - `run_external_script` (`task_runner.tasks.run_external_script`): sandboxed subprocess runner streaming stdout/stderr live to the browser.
  - `run_collectstatic` (`task_runner.tasks.run_collectstatic`): background static file collection.
- [x] Plugin Registry Integration:
  - Updated `AppPlugin` interface (`plugin_registry/base.py`) with `tasks` list and `get_tasks()` classmethod.
  - Added `get_all_tasks()` to `PluginRegistry` (`plugin_registry/registry.py`).
  - Created `TaskRunnerPlugin` in `task_runner/plugin.py` exposing background tasks in the dynamic menu.
- [x] Container Architecture:
  - Updated `docker-compose.yml` with `celery_worker` and `flower` services.
  - Updated `docker-compose.override.yml` with local development code volume bindings.
- [x] Automated Test Suite:
  - Created `tests/test_task_runner.py` with 19 comprehensive tests covering models, Celery tasks, Channels consumer, staff views, JSON API, admin script launcher, template tags, and plugin integration.
  - Entire test suite: **129 passed in 29.16s** with **81% total statement coverage**.

---

## 5. Milestone 12 — Bootstrap 5 Modernization, Custom Style Elimination & Theme Flexibility
- [x] **Retire Legacy Assets & Unify Baseline:**
  - [x] Removed legacy Bootstrap 3.3.7 JS (`templates/partials/scripts.html`) and updated `static/css/bootstrap.css` to Bootstrap 5.3.3.
  - [x] Vendored offline assets in `static/js/vendor/`: `bootstrap.bundle.min.js` (5.3.3), `htmx.min.js` (1.9.12), and `alpine.min.js` (3.14.0).
  - [x] Standardized completely on modern **Bootstrap 5.3+** matching CSS and JS bundle without jQuery dependency for core UI components.
- [x] **Eliminate All Ad-Hoc Inline Styles & Custom Hacks:**
  - [x] Audited and refactored all templates across apps (`task_runner`, `menu_management`, `user_management`, `todo`, `polls`, `home`, `templates/base.html`):
    - [x] Removed all inline styles (`style="margin-right: 10px;"`, `style="display: flex;"`, `style="padding: ...;"`).
    - [x] Removed custom modal CSS workarounds (`#launchTaskModal`, `.modal.in`, manual JS backdrops, `.task-type-tab`) in favor of native Bootstrap 5 modal components.
    - [x] Standardized on Bootstrap 5 spacing utilities (`gap-2`, `me-2`, `ms-2`, `d-flex`, `badge bg-*`).
    - [x] Standardized modal/interactive attributes exclusively on `data-bs-toggle="modal"`, `data-bs-target`, and `data-bs-dismiss="modal"`.
- [x] **Theme Architecture (`templates/themes/`):**
  - [x] Created `templates/themes/bootstrap5/` — pure native Bootstrap 5 templates (`base.html`, `partials/header.html`, `partials/footer.html`, `partials/styles.html`, `partials/scripts.html`, `partials/messages.html`, `partials/theme_selector.html`).
  - [x] Created `templates/themes/tailwind/` — Tailwind CSS template set with Alpine.js dropdowns and mobile drawer navigation.
  - [x] Created `templates/themes/minimal/` — bare semantic HTML5 template set with CSS custom properties and dark-mode readiness.
  - [x] Added `SITE_THEME` setting (default `'bootstrap5'`), `AVAILABLE_THEMES`, and dynamic `ThemeTemplateLoader` (`theme_management.loaders.ThemeTemplateLoader`).
  - [x] Created `theme_management` app with `ThemeMiddleware` (supporting `?theme=`, session, cookies, thread-local resolution) and `set_theme` view with OWASP open-redirect validation.
  - [x] Extended `AppPlugin` interface with `plugin_templates` dictionary mapping (`plugin_templates = {'bootstrap5': 'todo/bs5/', 'tailwind': 'todo/tw/'}`).
- [x] **HTMX & Alpine.js Integration:**
  - [x] Integrated HTMX for declarative AJAX partial page updates (e.g. `hx-post` for zero-reload todo item deletion).
  - [x] Integrated Alpine.js for lightweight UI state management (modals, dropdowns, tab switching) without jQuery or custom CSS hacks.
- [x] **Verification & Quality:**
  - [x] Created `tests/test_theme_management.py` with 17 comprehensive unit and integration tests.
  - [x] Verified zero modal overrides or ad-hoc inline styles.
  - [x] Full test suite passing: **146 passed in 31.56s** with **81% total statement coverage**.

---

## 6. Milestone 13 — Video Gallery Module
- [x] **Video Gallery Django Application:**
  - [x] Created `video_gallery` app with `VideoGallery` and `VideoItem` models.
  - [x] Support for YouTube, Vimeo, and direct MP4 file uploads / external URLs.
  - [x] Multi-format URL extraction engine (`video_gallery.utils`) for 11-char YouTube IDs and numeric Vimeo IDs.
  - [x] Automatic source type detection and video ID extraction on model `save()`.
  - [x] Comprehensive Django Admin (`video_gallery/admin.py`) featuring `VideoItemInline`, thumbnail list previews, video count badges, and live responsive 16:9 player preview in change forms.
- [x] **Plugin Registry & Dynamic Menus:**
  - [x] Registered `VideoGalleryPlugin` exposing "Media Gallery" under the "Apps" dropdown in navbar (`menu_management`).
  - [x] Fallback static menu links updated in `templates/base.html` and `templates/themes/bootstrap5/partials/header.html`.
- [x] **Public Catalog & Detail Views:**
  - [x] Gallery listing catalog at `/media/` (and `/videos/` alias redirect) with search and stats.
  - [x] Gallery detail view at `/media/<slug>/` with source filtering pills (All, YouTube, Vimeo, MP4) and within-gallery search.
  - [x] Zero custom CSS: standard Bootstrap 5.3+ spacing utilities, card layout, and `ratio-16x9` containers.
- [x] **Interactive Player & Media Previews:**
  - [x] Autoplay-on-hover for MP4 videos (`@mouseenter="$el.play()"` / `@mouseleave="$el.pause(); $el.currentTime = 0"`).
  - [x] Hover zoom and glowing play button overlays on provider thumbnails.
  - [x] Instant playback in native Bootstrap 5 + Alpine.js modal player (`partials/player_modal.html`) with zero reload and automatic audio silence on dismiss.
- [x] **Verification & Quality:**
  - [x] `manage.py check` → 0 issues.
  - [x] Created `tests/test_video_gallery.py` with 40 tests covering utils, models, views, admin, and plugin discovery (91% statement coverage).
  - [x] Total suite: **186 passed in 26.65s**, 0 failures.

---

## 7. Milestone 14 — CRM Module (Full-Featured)
- [x] **14a — Core CRM (Contacts & Leads):**
  - [x] Created `crm` Django application with `Company`, `Contact`, `Lead`, `InteractionLog` models.
  - [x] Standardized pipeline lifecycle stages (`NEW` → `CONTACTED` → `QUALIFIED` → `PROPOSAL` → `WON` / `LOST`).
  - [x] Custom CRM dashboard at `/crm/` with 4 KPI summary cards, pipeline value, stage distribution, recent deals, and activity feed.
  - [x] Django Admin panel (`crm/admin.py`) with `ContactInline`, `InteractionLogInline`, stage badges, and search filters.
  - [x] Registered `CRMPlugin` (`crm/plugin.py`) exposing CRM in dynamic navigation menu under "Apps".
- [x] **14b — Pipeline & Kanban View:**
  - [x] Interactive Kanban board (`/crm/pipeline/`) with 6 stage columns, count badges, and total dollar sums.
  - [x] Drag-and-drop capability using native HTML5 Drag and Drop events and AJAX stage updates.
  - [x] Non-drag dropdown menu on each deal card for accessible mobile and keyboard stage transitions.
  - [x] Automatic stage transition auditing logged to `InteractionLog`.
- [x] **14c — Automated Email Drip Sequences:**
  - [x] `EmailSequence` and `EmailStep` models with configurable delay days and dynamic placeholder templates.
  - [x] Auto-enrollment triggers on lead stage transitions (`auto_enroll_lead_in_sequences`).
  - [x] Celery background worker task (`crm.process_email_sequences`) with delay calculation and delivery tracking.
  - [x] 1x1 transparent tracking pixel endpoint (`/crm/track/<uuid:token>.png`) recording open events.
- [x] **14d — Customer Segmentation:**
  - [x] `Segment` model with dynamic JSON filter rules (`country`, `stage`, `min_value`, `tag`, `subscribed`).
  - [x] Dynamic query evaluation engine (`get_matching_contacts()`, `get_matching_leads()`).
  - [x] Segment broadcast email campaigns (`crm.send_segment_broadcast`) with delivery and touchpoint logs.
- [x] **14e — Analytics Dashboard:**
  - [x] Standalone analytics dashboard at `/crm/analytics/` and JSON API at `/crm/analytics/data/`.
  - [x] Vendored Chart.js 4.4.4 (`static/js/vendor/chart.umd.min.js`) for 100% offline rendering.
  - [x] 4 interactive charts: Lead funnel conversion, revenue by stage, monthly contacts growth, and email delivery/open rates.
- [x] **Verification & Quality:**
  - [x] `manage.py check` → **0 issues identified**.
  - [x] Multi-language i18n support across models, views, and templates (`makemessages` & `compilemessages` executed).
  - [x] Created `tests/test_crm.py` with 23 comprehensive tests (85% statement coverage on `crm` app).
  - [x] Total suite: **209 passed in 182.42s**, 0 failures across repository.

---

## 8. Milestone 15 — ERP Module (Modular Starter)
- [x] **15a — Product Catalog & Inventory Management:**
  - [x] Created `erp` Django app with `Product`, `Category`, `InventoryLocation`, `StockMovement`, and `StockMovementType` models.
  - [x] Automatic on-hand stock recalculation on stock movement persistence (in/out/adjustment/return).
  - [x] Dedicated inventory dashboard (`/erp/inventory/`) with valuation KPIs, category selector, low-stock filter, and stock alert banners.
  - [x] Background Celery beat task (`erp.check_low_stock_alerts`) checking reorder thresholds with email alerting.
  - [x] Product catalog CRUD (`/erp/products/`) with search, filter, and pagination.
- [x] **15b — Invoice Generation & Financial Operations:**
  - [x] `Invoice`, `InvoiceItem`, and `InvoiceStatus` models with subtotal, tax rate, discount, and total computation.
  - [x] ReportLab PDF engine (`erp/pdf.py`) generating professional branded invoices with line item tables and financial summaries.
  - [x] Invoice PDF download/preview endpoint (`/erp/invoices/<id>/pdf/`).
  - [x] Invoice email delivery task (`erp.send_invoice_email`) attaching generated PDF and updating status from `DRAFT` to `SENT`.
  - [x] Commercial invoice management (`/erp/invoices/`) with inline line item formsets and status transitions.
- [x] **15c — Executive ERP Dashboard & Modular Architecture:**
  - [x] Central ERP dashboard (`/erp/`) featuring 5 KPI summary cards (Products, Stock Value, Revenue, Outstanding, Low Stock).
  - [x] Interactive Chart.js charts: 6-month revenue trend, top products by valuation, inventory stock vs reorder thresholds.
  - [x] Sub-module pluggable extension stubs registered in `plugin_registry`:
    - `erp_procurement`: Supplier management and purchase orders.
    - `erp_warehouse`: Multi-location warehouse and bin topology.
    - `erp_accounting`: General ledger and chart of accounts.
  - [x] Architecture overview page (`/erp/modules/`) documenting plugin interfaces and technical specifications.
- [x] **Verification & Quality:**
  - [x] `manage.py check` → **0 issues identified**.
  - [x] `manage.py makemessages` & `compilemessages` clean across all 5 supported locales (es, fr, it, ja, pt).
  - [x] Created `tests/test_erp.py` with 20 comprehensive unit, task, view, PDF, and plugin tests (91% statement coverage on `erp`).
  - [x] Full test suite: **230 passed in 235.02s**, 0 failures across repository.


---

## 9. Milestone 16 — Intelligent Tracker Edge AI Security Hub Integration
- [x] **16a — Security REST API, Models & HMAC Webhook Receiver:**
  - [x] Created `intelligent_tracker_hub` app and registered `IntelligentTrackerPlugin` with `plugin_registry`.
  - [x] Implemented `SecurityAuditLog` and `SecurityEvent` models (UUID `event_id`, event types, site FK, camera ID, timestamp, snapshot crop, metadata JSON, resolution lifecycle).
  - [x] Implemented secure webhook endpoint `POST /api/v1/security/events/` in `rest_api` / `intelligent_tracker_hub`.
  - [x] Implemented HMAC-SHA256 signature verification (`X-Tracker-Signature`) validated against shared site secret using timing-attack safe comparison (`hmac.compare_digest`).
  - [x] Added `Location` model in `location_management` and registered in admin.
  - [x] Created SOC Dashboard at `/security/`, event detail view, resolution POST handler, and simulated edge dispatch tool.
  - [x] Automated test suite with 11 dedicated tests (90% statement coverage on `intelligent_tracker_hub`).
- [x] **16b — Video Evidence Ingestion & Zero-Copy Stream Gateway (`video_gallery`):**
  - [x] Implemented zero-copy registration endpoint `POST /api/v1/gallery/register/` storing edge video references, duration, camera ID, and ground-plane homography trajectories without duplicating MP4 files on Hub disk.
  - [x] Implemented on-demand streaming reverse proxy gateway `GET /api/v1/gallery/stream/<video_id>/` supporting HTTP 206 Partial Content / Range requests for smooth video scrubbing across NAT/WAN boundaries.
  - [x] Implemented dual-mode on-demand cloud archival `POST /api/v1/gallery/archive/<video_id>/` (and SOC UI button) for freezing evidence into central Hub storage on compliance hold.
  - [x] Implemented direct multipart upload `POST /api/v1/gallery/upload/` for backward compatibility.
  - [x] Auto-bound video to site gallery in `video_gallery.models.VideoGallery` (`security-audit-<site_slug>`) and linked to `SecurityEvent.video_evidence`.
  - [x] Updated SOC Event Detail UI (`event_detail.html`) to embed zero-copy video player with stream gateway URL and "Archive to Cloud Vault" action.
  - [x] Automated integration tests covering registration, stream proxy with range headers, archival trigger, and multipart upload (18 tests, 87% coverage).
- [x] **16c — Central Multi-Site Dashboard, Live Stream Gateway & Telemetry Canvas:**
  - [x] Created `Camera` model linked to `location_management.Location` with `camera_id`, `name`, `stream_url`, `status`, `last_heartbeat`, `fps`, and `resolution`.
  - [x] Implemented camera heartbeat endpoint `POST /api/v1/security/cameras/heartbeat/` tracking live edge health and status.
  - [x] Implemented authenticated live MJPEG streaming reverse proxy gateway `GET /api/v1/security/stream/live/<camera_id>/` traversing NAT/WAN firewalls without leaking edge private IPs.
  - [x] Implemented synthetic mock MJPEG stream generator and telemetry loop for offline edge simulation and CI/CD testing.
  - [x] Implemented real-time telemetry stream `GET /api/v1/security/stream/telemetry/<camera_id>/` and synchronized HTML5 Canvas overlay (30fps bounding boxes, track IDs, color-coded status).
  - [x] Modernized SOC Dashboard (`/security/`) with dynamic site selector, responsive multi-camera matrix grid (1x1, 2x2, 3x3), camera health badges, and live toast incident feed with Web Audio API chime.
- [x] **16d — Temporal CRM Visitor Passes, Whitelist Delta-Sync & Bi-directional Access Loop:**
  - [x] Extended CRM `Contact` with `security_clearance`, `valid_from`, `valid_until`, `license_plate`, `face_profile_photo`, `face_embedding_vector`, `security_tag`, `presence_status`, `last_seen_at`, and `last_seen_location`.
  - [x] Implemented helper methods: `is_pass_valid()`, `normalized_license_plate()`, `check_in()`, and `check_out()`.
  - [x] Implemented high-performance whitelist delta-sync API `GET /api/v1/security/whitelist/?site_id={site_id}` with HTTP ETag, `304 Not Modified`, and `?since=` delta filtering.
  - [x] Implemented gate access event ingestion endpoint `POST /api/v1/security/access/` updating CRM contact presence to "On-Premises" / "Checked In" (or "Off-Premises" on exit) and logging to `InteractionLog`.
  - [x] Defined offline-first edge SQLite `TrackerDB` schema, indexing, and sync specification in `documentation/INTELLIGENT_TRACKER_OFFLINE_DB_SPEC.md`.
  - [x] Triggered bilingual host arrival notifications via `intelligent_tracker_hub.notifications.send_visitor_arrival_notification` (EN/ES).
  - [x] Escalated banned/restricted intrusion attempts to `SecurityEvent` (`RESTRICTED_ENTITY`, `CRITICAL`).
  - [x] Modernized CRM Contact views (`contact_detail.html`, `contact_form.html`, `contact_list.html`) and SOC Operations Dashboard (`dashboard.html`).
- [x] **Verification & Quality:**
  - [x] Automated test suite covering whitelist ETag caching, delta sync, visitor access logs, ANPR matching, presence loops, and host notifications (41 tests in `tests/test_intelligent_tracker_hub.py`, 23 tests in `tests/test_crm.py`, 271 passed repository-wide).
  - [x] `manage.py check` → 0 issues identified.
  - [x] Translation catalogs compiled across all 5 locales.
  - [x] Responsive Bootstrap 5.3+ security operations dashboard.


