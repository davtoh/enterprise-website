# Enterprise Website → Django Starter Kit: Milestone Plan

> **Vision:** Transform the current `enterprise_website` project into a polished, AI-assisted Django starter-kit boilerplate. Developers clone this repo and run `python manage.py create_site` to scaffold a new fully-configured enterprise Django project. A future `pip`-installable `create-enterprise-site` CLI package will wrap this process for zero-clone onboarding.

---

## Design Decisions Summary

| Axis | Decision |
|---|---|
| **Project identity** | Django starter-kit template + `create_site` management command |
| **Module delivery** | Copy-and-customize into a standalone new project |
| **Always-on core** | Corporate Showcase (Home, About, Services, Products, Contact) |
| **Optional modules** | User Management, i18n/Rosetta, Todo, Polls, Brython, REST API, Dynamic Menus, CRM, ERP, Video |
| **Plugin architecture** | `AppPlugin` registry — each module declares menus, URLs, settings, API endpoints |
| **Dynamic Menus** | Auto-discovery from installed `AppPlugin`s + admin override panel |
| **CRM scope** | Full-featured: contacts/leads, pipeline, email sequences, segmentation, analytics |
| **ERP scope** | Modular: start lightweight (catalog, inventory, invoices), sub-modules added later |
| **Frontend stack** | Django templates + Bootstrap + HTMX + Alpine.js (CSS framework selectable in wizard) |
| **CSS framework** | Wizard choice: Bootstrap 5 (default), Tailwind, or minimal CSS |
| **Video** | Embed galleries (YouTube, Vimeo, MP4) with admin-managed model |
| **Background jobs** | Celery + Redis + Django Channels WebSockets for async tasks (FreeCAD/Blender/exports) |
| **Edge AI Vision & Security** | Microservice hub integration with `davtoh/intelligent-tracker` (Milestone 16) |
| **DevOps** | Docker, automated tests, production security headers, GitHub Actions CI/CD |
| **Future packaging** | `pip install create-enterprise-site` CLI that generates projects from this template |

---

## Completed Milestones (1–15)

| # | Title | Status |
|---|---|---|
| 1 | AI Rules & Standardization Setup | ✅ COMPLETE |
| 2 | Navigation & Page Routes Modernization | ✅ COMPLETE |
| 3 | Logic Fixes, Auth Modernization & Security Hardening | ✅ COMPLETE |
| 4 | Messages Refactoring & Environment Execution Standards | ✅ COMPLETE |
| 5 | Full Application Flash Messaging Integration | ✅ COMPLETE |
| 6 | Internationalization, Rosetta Mapping & Auto-Translation | ✅ COMPLETE |
| 7 | Documentation Consolidation & System Operations Manual | ✅ COMPLETE |
| 8 | Plugin Registry & Dynamic Menus System | ✅ COMPLETE |
| 9 | Automated Test Suite (106 tests, 80% coverage) | ✅ COMPLETE |
| 10 | Docker, CI/CD & Production Security | ✅ COMPLETE |
| 11 | Celery & Async Background Task Infrastructure | ✅ COMPLETE |
| 12 | Dynamic Menus: CSS Selector, Bootstrap 5 Modernization & Custom Style Elimination | ✅ COMPLETE |
| 13 | Video Gallery Module | ✅ COMPLETE |
| 14 | CRM Module (Full-Featured: Contacts, Pipeline, Email Sequences, Segmentation, Analytics) | ✅ COMPLETE |
| 15 | ERP Module (Modular Starter: Catalog, Inventory, Invoices, Dashboard) | ✅ COMPLETE |

---

### [Milestone 8] — Plugin Registry & Dynamic Menus System
**Status:** **COMPLETE** (2026-10-21)  
**Scope:** Architectural foundation. Every subsequent module plugs into this.

**Objectives:**
- Define `AppPlugin` base class in a new `plugin_registry` app:
  - Declares: `name`, `label`, `menu_items`, `url_namespace`, `settings_defaults`, `api_endpoints`, `dependencies`, `icon`
  - Each existing app (`todo`, `polls`, `home`, `user_management`, etc.) gets its own `plugin.py` implementing `AppPlugin`
  - Plugin manager auto-discovers all installed `AppPlugin` subclasses via Django app registry
- Build `menu_management` Django app:
  - `MenuItem` model: label, url_name/url_external, icon, order, parent (nested menus), visible, plugin_source
  - Admin panel to create, reorder (drag-and-drop), hide, and add external link items
  - Auto-populates from discovered `AppPlugin.menu_items` on app startup (respects overrides)
  - Context processor injects menu tree into all templates
  - Update `base.html` navbar to render dynamic menu tree instead of hardcoded links
- Update `TODO_MODERNIZATION.md` and `MIGRATION_LOG.md`
- Write `documentation/plugin_system.md` explaining how to create a new plugin

**Verification:**
- `manage.py check` → 0 issues
- Navbar renders dynamically from database
- Admin can hide/reorder menu items
- Adding/removing an app from `INSTALLED_APPS` automatically reflects in menu

---

### [Milestone 9] — Automated Test Suite
**Status:** **COMPLETE** (2026-10-22)  
**Scope:** Stabilize the current codebase with comprehensive tests before adding new features.

**Objectives:**
- [x] Configure `pytest-django` with `pytest.ini` / `pyproject.toml`
- [x] Write test modules for each existing app:
  - [x] `tests/test_home.py` — all 5 pages return 200, contact form submission
  - [x] `tests/test_user_management.py` — signup, login, logout, profile update, activation flow
  - [x] `tests/test_todo.py` — add, complete, delete, detail views; authentication enforcement
  - [x] `tests/test_polls.py` — list, vote, results; duplicate vote prevention
  - [x] `tests/test_language_management.py` — language switch, `auto_translate` command
  - [x] `tests/test_timezone_management.py` — timezone switch middleware
  - [x] `tests/test_plugin_registry.py` — plugin discovery, menu auto-population
  - [x] `tests/test_rest_api.py` — DRF endpoint health checks
  - [x] `tests/test_webprogram.py` — Brython webprogram views
  - [x] `tests/test_utils_and_extra.py` — referer helper & form avatar validations
- [x] Add `coverage` reporting (`pytest --cov=. --cov-report=html`)
- [x] Target: ≥80% coverage across all apps (Achieved: 80% with 106 passing tests)
- [x] Update `requirements/local.txt` with test dependencies (`pytest-cov>=4.1.0`)

**Verification:**
- `pytest` runs cleanly: 106 passed in 22.03s, 0 failures
- Coverage report generated in `htmlcov/` (80% total statement coverage)
- `manage.py check` → 0 issues


---

### [Milestone 10] — Docker, CI/CD & Production Security
**Scope:** Make the starter kit deployable and automatically validated.

**Objectives:**
- [x] **Docker:**
  - [x] `Dockerfile` — multi-stage build (builder + slim runtime with non-root appuser)
  - [x] `docker-compose.yml` — services: `web` (Django/Daphne), `db` (PostgreSQL 16), `redis` (7 for Channels + future Celery), `nginx` (1.27 static files + reverse proxy)
  - [x] `docker-compose.override.yml` — local dev overrides (SQLite mode, debug, volume mounts)
  - [x] `.dockerignore` — exclude `.venv`, `*.pyc`, `world.sql`, media, etc.
- [x] **Production Security Headers** in `settings.py`:
  - [x] `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
  - [x] `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`
  - [x] `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_PROXY_SSL_HEADER`
  - [x] Guard all headers behind `DEBUG=False` conditional with environment overrides
- [x] **GitHub Actions CI/CD** (`.github/workflows/ci.yml`):
  - [x] On push/PR: install deps → `compilemessages` → `manage.py check` → `manage.py check --deploy` → `pytest --cov` → upload coverage report artifact
  - [x] On tag/release: build Docker image with Buildx → push to GitHub Container Registry (`ghcr.io`)
- [x] **world.sql cleanup & on-demand download:**
  - [x] Keep `world.sql` and `world.sql.json` out of git history (verified in `.gitignore` and `.dockerignore`)
  - [x] Add a `download_geodata.py` management command that fetches them on demand from upstream repository or archive
  - [x] Document in `README.md` and `documentation/README.md`

**Verification:**
- `docker compose config` and `docker compose -f docker-compose.yml config` validate with 0 syntax/structure errors
- `python manage.py check` → 0 issues
- `python manage.py check --deploy` with production environment flags → 0 issues
- 109 unit & integration tests passing with 80% code coverage
- CI workflow validated at `.github/workflows/ci.yml`

---

### [Milestone 11] — Celery & Async Background Task Infrastructure
**Scope:** Enable long-running background jobs (renders, exports, AI calls, external programs) with real-time WebSocket progress updates.

**Objectives:**
- [x] Install and configure `celery` + `redis` (broker + result backend)
- [x] Create `task_runner` Django app:
  - [x] `TaskJob` model: task_id, name, status (pending/running/success/failure), progress %, log output, created_by, created_at
  - [x] Celery task base class with automatic `TaskJob` status updates
  - [x] Django Channels consumer that streams `TaskJob` updates via WebSocket to the requesting browser
  - [x] A reusable `{% task_progress_widget task_id %}` template tag for any page
- [x] Example tasks:
  - [x] `run_auto_translate` — existing `auto_translate` command as async Celery task
  - [x] `run_external_script` — sandboxed subprocess runner (stdin/stdout/stderr streamed live)
  - [x] `run_collectstatic` — background static file collection
- [x] Update `AppPlugin` interface to allow plugins to register their own Celery tasks
- [x] `docker-compose.yml` updated with `celery_worker` and `flower` (task monitor) services

**Verification:**
- [x] Submit a task from admin / web UI → see real-time progress in browser
- [x] Failed tasks report error messages in `TaskJob` log
- [x] `manage.py check` → 0 issues
- [x] 128 tests passing (18 dedicated task_runner unit/integration tests) with 81% total statement coverage

---

### [Milestone 12] — Dynamic Menus: CSS Framework Selector, Bootstrap 5 Modernization & Custom Style Elimination
**Scope:** Modernize the entire frontend presentation layer to clean Bootstrap 5.3, retire legacy Bootstrap 3 JS + Bootstrap 4 CSS mismatches, and eliminate all ad-hoc inline styles and custom modal workarounds across the codebase.

**Objectives:**
- [x] **Retire Legacy Assets & Unify Framework Baseline:**
  - [x] Remove outdated CDN Bootstrap 3.3.7 JS (`templates/partials/scripts.html`) and legacy Bootstrap 4.0-beta CSS (`static/css/bootstrap.css`).
  - [x] Standardize completely on modern **Bootstrap 5.3+** with matching CSS and JS bundle (eliminating jQuery dependency for core UI components).
- [x] **Eliminate All Ad-Hoc Inline Styles & Custom Hacks:**
  - [x] Audit and clean all project templates (including `task_runner`, `menu_management`, `user_management`, `todo`, `polls`, `home`):
    - [x] Remove all inline styles (e.g. `style="margin-right: 10px;"`, `style="display: flex;"`, `style="z-index: ...;"`).
    - [x] Remove custom modal CSS workarounds (such as `#launchTaskModal` display/opacity overrides, `.modal.in`, manual JS backdrops, `.task-type-tab`).
    - [x] Replace with standard Bootstrap 5 utility classes (`gap-2`, `me-2`, `ms-2`, `d-flex`, `form-select`, `badge bg-*`).
    - [x] Standardize interactive component attributes exclusively on native Bootstrap 5 `data-bs-toggle="modal"`, `data-bs-target`, and `data-bs-dismiss="modal"`.
- [x] **Create Theme Architecture (`templates/themes/`):**
  - [x] `bootstrap5/` — pure native Bootstrap 5 templates (base, navbar, cards, forms, alerts, modals)
  - [x] `tailwind/` — Tailwind CSS equivalent templates (with CDN fallback and PostCSS build option)
  - [x] `minimal/` — bare semantic HTML5 with CSS custom properties only
- [x] **Settings & Dynamic Resolution:**
  - [x] Add `SITE_THEME` setting (default `'bootstrap5'`) controlling active theme template directory.
  - [x] Template loader resolving `base.html`, `partials/messages.html`, etc. from `templates/themes/{SITE_THEME}/`.
  - [x] `AppPlugin` template declaration per theme (`plugin_templates = {'bootstrap5': 'todo/bs5/', 'tailwind': 'todo/tw/'}`).
- [x] **HTMX & Alpine.js Integration:**
  - [x] Add lightweight HTMX for declarative AJAX partial page updates (e.g. task progress polling, todo item toggle/delete).
  - [x] Add Alpine.js for client-side state (modals, dropdowns, collapsible consoles) without jQuery or custom style manipulation.

**Verification:**
- [x] Zero custom inline styles or modal CSS overrides remaining in codebase.
- [x] Switching `SITE_THEME` to `'tailwind'` renders the full site in Tailwind without breaking any views.
- [x] HTMX operations execute without full page reloads.
- [x] Bootstrap 5 / Alpine.js powers all modals, dropdowns, and collapse components cleanly across mobile and desktop.
- [x] 146 tests passing with 81% total statement coverage (17 dedicated theme_management tests).


---

### [Milestone 13] — Video Gallery Module
**Scope:** Admin-managed embed-based video galleries (YouTube, Vimeo, MP4).

**Objectives:**
- [x] Create `video_gallery` Django app:
  - [x] `VideoItem` model: title, description, thumbnail, source_type (youtube/vimeo/mp4), embed_url/file, gallery (FK), order, is_active, created_at, updated_at
  - [x] `VideoGallery` model: name, slug, description, is_active, timestamps
  - [x] Admin panel with preview thumbnails, video count badges, and embedded live player previews
- [x] `AppPlugin` registration with menu item "Media Gallery"
- [x] Public view: gallery listing page (`/media/`) and gallery detail (`/media/<slug>/`) with responsive video grid and search/filter
- [x] Responsive HTML5/iframe player component with autoplay-on-hover for thumbnails and Bootstrap 5 modal player
- [x] YouTube/Vimeo URL parser that extracts embed ID from share URLs automatically
- [x] i18n wrapper for all user-facing strings

**Verification:**
- [x] Create gallery with YouTube + Vimeo + MP4 items in admin → renders correctly in browser
- [x] Responsive on mobile (Bootstrap 5.3+ ratio containers, card grid, flex-wrap pills)
- [x] `manage.py check` → 0 issues
- [x] 186 tests passing with 91% statement coverage on `video_gallery` (40 dedicated tests)

---

### [Milestone 14] — CRM Module (Full-Featured)
**Scope:** Full customer relationship management with pipeline, email sequences, segmentation, and analytics.

**Sub-modules (implemented incrementally within this milestone):**

**14a — Core CRM (Contacts & Leads):**
- [x] `crm` Django app with `Contact`, `Company`, `Lead`, `InteractionLog` models
- [x] Lead status pipeline (New → Contacted → Qualified → Proposal → Won/Lost)
- [x] Admin panel + custom CRM dashboard at `/crm/`
- [x] `AppPlugin` registration

**14b — Pipeline & Kanban View:**
- [x] Drag-and-drop Kanban board (HTMX + Alpine.js) showing leads by pipeline stage
- [x] Stage transitions logged automatically to `InteractionLog`

**14c — Email Sequences:**
- [x] `EmailSequence` and `EmailStep` models
- [x] Celery task that auto-sends emails based on lead stage and time delays
- [x] Email template editor in admin with placeholder tags
- [x] 1x1 transparent tracking pixel for email open analytics

**14d — Customer Segmentation:**
- [x] `Segment` model with filter rules (e.g., "all leads in stage=Qualified from country=US")
- [x] Dynamic segment membership evaluation
- [x] Segment-based email broadcast campaign

**14e — Analytics Dashboard:**
- [x] Charts (vendored Chart.js 4.4.4) showing: lead funnel conversion, monthly new contacts, email open rates, revenue pipeline value
- [x] Django admin analytics panel + standalone `/crm/analytics/` page

**Verification:**
- [x] Full lead lifecycle from creation to Won/Lost with interaction log
- [x] Email sequence auto-sends via Celery (`crm.process_email_sequences`)
- [x] Analytics charts render with real data (API endpoint at `/crm/analytics/data/`)
- [x] i18n applied to all strings (`makemessages` & `compilemessages` clean)
- [x] 209 tests passing repository-wide with 85% coverage on `crm` app (23 dedicated tests)

---

### [Milestone 15] — ERP Module (Modular Starter)
**Scope:** Lightweight ERP core with architecture for future sub-module expansion.

**15a — Product Catalog & Inventory:**
- [x] `erp` Django app with `Product`, `Category`, `StockMovement`, `InventoryLocation` models
- [x] Admin panel + `/erp/inventory/` dashboard
- [x] Low-stock alerts (Celery beat task `erp.check_low_stock_alerts`)

**15b — Invoice Generation:**
- [x] `Invoice`, `InvoiceItem`, `InvoiceStatus` models
- [x] PDF invoice generation with ReportLab (`generate_invoice_pdf`)
- [x] Invoice download endpoint (`/erp/invoices/<id>/pdf/`) + email delivery (`erp.send_invoice_email`)
- [x] Basic accounting: total revenue, outstanding invoices, financial KPI metrics

**15c — ERP Dashboard:**
- [x] Key metrics: total products, stock value, monthly revenue, outstanding invoices, low-stock count
- [x] Charts (vendored Chart.js 4.4.4): revenue trend, top products by value, inventory levels vs reorder threshold

**Future sub-modules (stubs registered in plugin registry, architecture documented):**
- [x] `erp_procurement` — purchase orders, supplier management (`ERPProcurementPlugin`)
- [x] `erp_warehouse` — multi-location stock tracking (`ERPWarehousePlugin`)
- [x] `erp_accounting` — full general ledger (`ERPAccountingPlugin`)

**Verification:**
- [x] Create products, record stock movements with automatic on-hand recalculation, generate downloadable & printable PDF invoice
- [x] Dashboard displays correct real-time metrics and Chart.js visualizations
- [x] Sub-module stubs visible and clearly marked as "coming soon" in the UI (`/erp/modules/` and `/erp/`)
- [x] Multi-language i18n support across models, views, forms, and templates (`makemessages` & `compilemessages`)
- [x] 230 tests passing repository-wide with 91% statement coverage on `erp` app (20 dedicated tests)

---

## Upcoming Milestones

---

### [Milestone 16] — Intelligent Tracker Edge AI Security Hub Integration
**Scope:** Edge AI Vision & Spatial Security Hub Integration connecting [davtoh/enterprise-website](https://github.com/davtoh/enterprise-website) with [davtoh/intelligent-tracker](https://github.com/davtoh/intelligent-tracker) (Edge AI Vision Microservice). Offloads GPU-heavy edge inference (YOLOv8/11 + OSNet + SORT tracking) to distributed edge nodes while `enterprise_website` serves as the centralized multi-site command and auditing hub.

> **Feasibility Assessment (Edge Independence):** Work on this milestone proceeds immediately on `enterprise_website` without waiting for `intelligent-tracker` completion. In this edge-cloud architecture, `enterprise_website` is the server defining the contracts (`POST /api/v1/security/events/`, `POST /api/v1/gallery/upload/`, `GET /api/v1/security/whitelist/`). All Hub models, webhook receivers, HMAC authentication, multi-site UI, and test suites are 100% testable via mock edge payloads and stream simulation.

**16a (Phase E1) — Security REST API, Models & HMAC Webhook Receiver:**
- [x] Create `intelligent_tracker_hub` Django app and register `IntelligentTrackerPlugin` with `plugin_registry`.
- [x] Implement `SecurityAuditLog` and `SecurityEvent` models:
  - `event_id`: Unique UUID.
  - `event_type`: Choices (`IntrusionAlert`, `RestrictedEntityAlert`, `OccupancyThresholdEvent`, `FallDetectedAlert`, `LoiteringAlert`, `LineCrossAlert`).
  - `site`: ForeignKey to `location_management.models.Location`.
  - `camera_id`: Source camera feed identifier (e.g., `cam-north-01`).
  - `timestamp`: UTC ISO-8601 timestamp.
  - `snapshot`: Evidence crop image field with Base64 JPEG/PNG decoding storage.
  - `metadata`: JSONField storing zone name, dwell duration, confidence score, recognized entity ID/name.
  - `severity`: Choices (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) with automatic type-based severity mapping.
  - Resolution workflow: `is_resolved`, `resolved_by`, `resolved_at`, `resolution_notes`, and `resolve()` method.
- [x] Implement secure webhook endpoint: `POST /api/v1/security/events/` in `rest_api` / `intelligent_tracker_hub`.
- [x] Implement HMAC-SHA256 signature verification (`X-Tracker-Signature`) validated against shared site secret with timing-attack safe comparison (`hmac.compare_digest`).
- [x] Register models in Django Admin with live thumbnail previews, severity badges, and formatted JSON telemetry.
- [x] Build SOC Dashboard at `/security/` with real-time KPI metrics, filter bars, event detail inspection, incident resolution form, and interactive edge webhook simulation tool.
- [x] Add `Location` model to `location_management` with code, city, and coordinates.
- [x] Automated test suite (11 dedicated tests, 90% statement coverage on `intelligent_tracker_hub`) validating HMAC verification, tampering detection, payload schemas, model methods, and dashboard views.

**16b (Phase E2) — Video Evidence Ingestion & Zero-Copy Stream Gateway (`video_gallery`):**
- [x] Lightweight Zero-Copy Registration endpoint: `POST /api/v1/gallery/register/` storing edge video references, duration, camera ID, and ground-plane homography trajectories without Hub disk storage duplication.
- [x] On-Demand Streaming Reverse Proxy Gateway: `GET /api/v1/gallery/stream/<video_id>/` supporting HTTP 206 Partial Content / Range requests for seamless video scrubbing across NAT/WAN boundaries.
- [x] Dual-Mode On-Demand Cloud Archival: `POST /api/v1/gallery/archive/<video_id>/` (and SOC UI button) for freezing evidence into central Hub storage on compliance hold.
- [x] Direct Multipart Upload fallback: `POST /api/v1/gallery/upload/` accepting direct MP4 file uploads from isolated edge nodes.
- [x] Auto-bind video to site gallery in `video_gallery.models.VideoGallery` (e.g. `security-audit-<site_slug>`) and link to `SecurityEvent.video_evidence`.
- [x] Update SOC Event Detail UI (`event_detail.html`) to embed zero-copy video player with stream gateway URL and "Archive to Cloud Vault" action.
- [x] Automated integration test suite (18 dedicated tests, 87% statement coverage on `intelligent_tracker_hub`, 248 passed repository-wide) validating zero-copy registration, streaming proxy with range headers, archival trigger, and multipart upload.

**16c (Phase E3) — Central Multi-Site Dashboard, Live Stream Gateway & Telemetry Canvas:**
- [x] Camera Registry & Dynamic Health Model:
  - Create `Camera` model linked to `location_management.Location` with `camera_id`, `name`, `stream_url`, `status` (`ONLINE`, `OFFLINE`, `CONNECTING`, `DEGRADED`), `last_heartbeat`, `fps`, and `resolution`.
  - Heartbeat receiver endpoint: `POST /api/v1/security/cameras/heartbeat/` tracking live edge health and connection state.
- [x] Authenticated Live MJPEG Streaming Reverse Proxy Gateway:
  - `GET /api/v1/security/stream/live/<camera_id>/` proxying edge MJPEG feeds across NAT/WAN firewalls without leaking edge private LAN IPs.
  - Built-in synthetic mock MJPEG generator fallback for local testing, CI/CD, and offline demos.
- [x] Real-time Telemetry Stream & HTML5 Canvas Overlay:
  - Telemetry endpoint `GET /api/v1/security/stream/telemetry/<camera_id>/` delivering 30fps bounding box annotations (`[ymin, xmin, ymax, xmax]`), track IDs, person labels, and intrusion vectors.
  - Synchronized HTML5 Canvas overlay rendering color-coded classification tags (Green = Staff/VIP, Yellow = Visitor, Red = Intrusion/Restricted).
- [x] Enhanced SOC Multi-Site Operations Center Dashboard (`/security/`):
  - Dynamic multi-site selector connected to `location_management.Location`.
  - Multi-camera responsive matrix grid (1x1, 2x2, 3x3 layout selector) on Bootstrap 5.3+.
  - Live camera card grid displaying real-time connection status badges, FPS, and latency.
  - Real-time incident alert drawer with Bootstrap 5 toasts and Web Audio API chime toggle.
- [x] Automated integration test suite (28 dedicated tests, 86% statement coverage on `intelligent_tracker_hub`, 258 passed repository-wide) validating Camera models, heartbeat ingestion, synthetic MJPEG streams, fallback proxying, telemetry overlays, and SOC multi-site rendering.

**16d (Phase E4) — Temporal CRM Visitor Passes, Whitelist Delta-Sync & Bi-directional Access Loop:**
- [ ] Extend CRM `Contact` with enterprise physical security credentials:
  - `security_clearance`: Choices (`VIP`, `STAFF`, `CONTRACTOR`, `VISITOR`, `RESTRICTED`, `BANNED`).
  - `valid_from` & `valid_until`: Time-bound validity window for contractor passes and visitor clearances.
  - `license_plate`: Alphanumeric normalized vehicle license plate for ANPR gate recognition.
  - `face_profile_photo`: Biometric reference image for edge facial recognition vector generation.
  - `face_embedding_vector`: Pre-computed 512-d biometric embedding for zero-latency edge startup.
  - `security_tag`: Custom tag for edge tracker classification.
- [ ] High-Performance Whitelist Delta-Sync API:
  - `GET /api/v1/security/whitelist/?site_id={site_id}` supporting HTTP ETag (`If-None-Match`), `304 Not Modified`, and `?since=` delta-sync filtering to minimize WAN bandwidth.
  - Automatically filters out expired visitor passes and revoked credentials.
- [ ] Bi-directional Access Loop & CRM Presence Tracking:
  - Ingestion endpoint: `POST /api/v1/security/access/` recording gate access events.
  - Automatically updates contact CRM presence state to "On-Premises" / "Checked In" with audit timeline entry.
  - Triggers automated bilingual arrival alerts via `language_management` catalogs (EN/ES).
- [ ] Offline-First Edge Cache Architecture:
  - Define local SQLite `TrackerDB` schema and sync specification for `davtoh/intelligent-tracker`.

**Verification:**
- Automated test suite covering camera streams, heartbeats, whitelist ETag caching, visitor access logs, and CRM contact synchronization.
- `python manage.py check` → 0 issues.
- Responsive Bootstrap 5.3+ security operations dashboard.

---

### [Milestone 17] — `create_site` Scaffolding Wizard
**Scope:** The flagship feature — the interactive `manage.py create_site` command that generates a new standalone Django project from this template.

**Objectives:**
- `management/commands/create_site.py` interactive wizard:
  - Prompts: project name, display name, description, target directory
  - CSS framework choice: Bootstrap 5 / Tailwind / Minimal
  - Language selection (supported locales)
  - Module selection (checkboxes for each registered `AppPlugin`, including CRM, ERP, Video, Intelligent Tracker Hub)
  - Database preference (SQLite / MySQL / PostgreSQL)
  - Docker support (yes/no)
  - Optional: `--ai` flag — calls Gemini/OpenAI with a project description prompt to auto-suggest module selection and generate homepage copy
- Generation engine:
  - Copies core project structure + selected app directories to target
  - Updates `settings.py` (INSTALLED_APPS, DATABASES, LANGUAGES, SITE_THEME)
  - Updates `urls.py` root URLconf
  - Generates `.env.example` with relevant keys for chosen modules
  - Generates `requirements.txt` combining only the needed dependencies
  - Generates `docker-compose.yml` if Docker selected
  - Runs `makemessages` and `auto_translate` bootstrap for selected languages
  - Prints a "Next Steps" checklist to the terminal
- Write `documentation/create_site.md` with full wizard usage guide

**Verification:**
- `python manage.py create_site` generates a functional standalone project
- Generated project passes `manage.py check` → 0 issues
- Generated project passes `migrate` and `runserver` cleanly
- `--ai` flag generates sensible module selection and homepage copy (if API key present)

---

### [Milestone 18] — Packaging: `create-enterprise-site` pip CLI
**Scope:** Make the starter kit consumable without cloning — via a pip package.

**Objectives:**
- Create separate `create-enterprise-site` Python package (sibling directory or separate repo)
- CLI entry point: `create-enterprise-site my-new-project-name`
- Internally: downloads/clones this template repo, runs `create_site` wizard non-interactively using CLI args, or interactively
- Publish to PyPI
- Update root `README.md` with one-liner: `pip install create-enterprise-site && create-enterprise-site my-project`

**Verification:**
- `pip install create-enterprise-site` works from PyPI
- `create-enterprise-site demo-project` generates a clean runnable project
- Works on Windows, Linux, macOS

---

## Deferred / Future Phases

| Feature | Reason for Deferral |
|---|---|
| Face Recognition (In-Process ML) | Heavy deep-learning/PyTorch dependencies offloaded to Edge AI microservice (`davtoh/intelligent-tracker`) via Milestone 16 Hub integration |
| `erp_procurement` sub-module | ERP core needed first; procurement is large scope |
| `erp_accounting` sub-module | Requires accounting expertise, regulatory compliance |
| FreeCAD / Blender rendering | Celery infra (Milestone 11) must be solid first; add as example Celery task after |
| WebRTC video conferencing | Channels infra available but feature is standalone scope |
| React/Vue SPA frontend | Alpine.js + HTMX covers most needs; React becomes viable after REST API matures |

---

## Dependency Graph

```
M8 (Plugin Registry)
  └── M9 (Tests)
  └── M12 (Theme/CSS Selector)
  └── M13 (Video Gallery) ─────────┐
  └── M14 (CRM) ───────────────────┤
  └── Location Management ─────────┼──> M16 (Intelligent Tracker Hub)
                                   │      └── M17 (create_site Wizard)
M10 (Docker + CI/CD)               │          └── M18 (pip CLI)
  └── M11 (Celery)                 │
      └── M14 (CRM)                │
      └── M15 (ERP) ───────────────┘
```

---

## Notes for NOTES.txt Items

| NOTES.txt Item | Addressed In |
|---|---|
| `() dynamic menus` | Milestone 8 |
| `() ERP` | Milestone 15 |
| `() CRM` | Milestone 14 |
| `() Integrate video visualization` | Milestone 13 |
| `() Integrate javascript` | Milestone 12 (HTMX + Alpine.js; React-ready architecture) |
| `() Integrate face recognition` | Milestone 16 (Intelligent Tracker Edge AI Security Hub Integration) |
| `WARNING bootstrap.min.css.map 404` | Fix in Milestone 9 (minor task alongside test setup) |
