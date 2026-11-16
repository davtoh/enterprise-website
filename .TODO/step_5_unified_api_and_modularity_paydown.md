# Step 5 Implementation Plan: Unified `/api/v1/` (`drf-spectacular`), Ecosystem Ops & Modularity Paydown

**Plan Slug:** `step_5_unified_api_and_modularity_paydown`  
**Parent Master Plan:** `platform_evolution_master_roadmap` (Master Milestone 5)  
**Architecture Reference:** `docs/ARCHITECTURE.md` (Sections 2.2, 4, 6 & 7)  
**Execution Mode:** 1-Milestone-Per-Turn Execution Gate (`plan_engine.py`)

---

## 1. Executive Summary

This child plan executes **Master Step 5** (the final step of `platform_evolution_master_roadmap`) across 3 cohesive, vertically verified milestones:
1. **Milestone 1 (Unified `/api/v1/` OpenAPI 3 Gateway via `drf-spectacular` & `AppPlugin.api_urlpatterns` Auto-Mounting — ACTIVE EXECUTION TARGET)**: Add `drf-spectacular`, `django-filter`, `django-import-export`, and `django-htmx` to project dependencies and settings; mount `/api/v1/schema/` (OpenAPI 3 YAML/JSON), `/api/v1/docs/` (Swagger UI), and `/api/v1/redoc/` (Redoc); add a module-level `get_active_api_urlpatterns()` helper in `plugin_registry/registry.py` (preserving the $\le 12$-method budget on `PluginRegistry`); register plugin API routes (`rest_api`, `crm`, `erp`, `polls`) under `/api/v1/` alongside existing HMAC-secured `intelligent_tracker_hub` routes while keeping `/rest_api/` 100% backwards-compatible.
2. **Milestone 2 (Ecosystem Operations: `django-filter`, `django-import-export` & `django-htmx` Across `crm`, `erp` & `location_management` — DEFERRED TO NEXT TURN / MILESTONE)**: Add `ModelResource` classes (`crm/resources.py`, `erp/resources.py`, `location_management/resources.py`) and wire `ImportExportModelAdmin` into Unfold admin classes (`crm/admin.py`, `erp/admin.py`, `location_management/admin.py`); add declarative `FilterSet` modules (`crm/filters.py`, `erp/filters.py`); enable `HtmxMiddleware` and wire `FilterSet` + `request.htmx` partial table rendering into `crm` and `erp` list views.
3. **Milestone 3 (Modularity Budget Paydown for `erp/pdf.py`, `intelligent_tracker_hub/api/*.py` & `dashboard.html` + Final Master Roadmap Sign-Off — DEFERRED TO NEXT TURN / MILESTONE)**: Decompose `erp/pdf.py::generate_invoice_pdf` (248L $\to \le 35$L orchestrator + $\le 40$L flowable helpers); refactor oversized webhook/stream handlers in `intelligent_tracker_hub/api/access_control.py` (`post`: 195L), `video_evidence.py` (`post`: 135L & 110L), `security_events.py` (`post`: 131L), and `video_streaming.py` (`get`: 129L, `post`: 83L) so every function is $\le 40$ lines and every file is $< 350$ lines; split `intelligent_tracker_hub/templates/intelligent_tracker_hub/dashboard.html` (630L) into 7 focused partials under `intelligent_tracker_hub/templates/intelligent_tracker_hub/partials/`; and run the full regression suite, static modularity audit, defect scan, and final `plan_engine.py digest`.

---

## 2. Quantitative Modularity & Target Budgets

| Target File | Current Lines | Planned Net Lines | Budget Status | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `plugin_registry/registry.py` | 178L (12 methods) | ~195L (12 methods) | **PASS** (< 350L, $\le 12$M) | Module-level `get_active_api_urlpatterns()` helper ($\le 40$L/fn) |
| `rest_api/v1_urls.py` | 0L (New) | ~45L | **PASS** (< 350L) | Unified `/api/v1/` schema, Swagger/Redoc docs & active plugin router aggregator |
| `rest_api/plugin.py` | 11L | ~25L | **PASS** (< 350L) | Expose `api_urlpatterns` for `/api/v1/users/` |
| `crm/filters.py` & `crm/resources.py` | 0L (New) | ~75L each | **PASS** (< 350L) | `CompanyFilter`, `ContactFilter`, `LeadFilter` & `import_export` resources |
| `erp/filters.py` & `erp/resources.py` | 0L (New) | ~75L each | **PASS** (< 350L) | `ProductFilter`, `InvoiceFilter`, `StockMovementFilter` & `import_export` resources |
| `location_management/resources.py` | 0L (New) | ~45L | **PASS** (< 350L) | `CountriesResource`, `StatesResource`, `CitiesResource`, `LocationResource` |
| `crm/admin.py` & `erp/admin.py` | 218L / 120L | ~240L / ~140L | **PASS** (< 350L) | Unfold + `ImportExportModelAdmin` integration |
| `erp/pdf.py` | 264L (248L fn) | ~260L ($\le 40$L/fn) | **PASS** (< 350L, $\le 40$L/fn) | Decompose `generate_invoice_pdf` into 6 focused ReportLab flowable helpers |
| `intelligent_tracker_hub/api/access_control.py` | 263L (195L fn) | ~275L ($\le 40$L/fn) | **PASS** (< 350L, $\le 40$L/fn) | Decompose `SecurityAccessIngestApiView.post` into 6 single-purpose helpers |
| `intelligent_tracker_hub/api/video_evidence.py` | 336L (135L & 110L fn) | ~290L ($\le 40$L/fn) | **PASS** (< 350L, $\le 40$L/fn) | Decompose `VideoEvidenceRegisterApiView.post` & `VideoEvidenceUploadApiView.post` |
| `intelligent_tracker_hub/api/security_events.py` | 250L (131L fn) | ~255L ($\le 40$L/fn) | **PASS** (< 350L, $\le 40$L/fn) | Decompose `SecurityEventWebhookApiView.post` into validation/persistence helpers |
| `intelligent_tracker_hub/api/video_streaming.py` | 255L (129L & 83L fn) | ~260L ($\le 40$L/fn) | **PASS** (< 350L, $\le 40$L/fn) | Decompose `VideoEvidenceStreamGatewayApiView.get` & `VideoEvidenceArchiveApiView.post` |
| `intelligent_tracker_hub/templates/intelligent_tracker_hub/dashboard.html` | 630L (HARD) | ~55L (+ 7 partials $\le 170$L) | **PASS** (< 350L) | Extract KPI cards, matrix toolbar, video matrix, filters, events table, gate log, and JS |

---

## 3. Surface Invariants & Public API Contracts

1. **Backwards-Compatible `/rest_api/` & `rest_api` Namespace**:
   - Existing routes `/rest_api/` (`rest_api:api-root`), `/rest_api/users/` (`rest_api:siteuser-list`), and `/rest_api/users/<pk>/` (`rest_api:siteuser-detail`) must remain mounted and pass all assertions in `tests/test_rest_api.py` (including `IsAuthenticated` 403 for anonymous callers and self-scoped queryset for non-staff).
2. **Edge AI HMAC Webhook & Stream Contract (`/api/v1/security/*`, `/api/v1/cameras/*`, `/api/v1/gallery/*`)**:
   - All existing `intelligent_tracker_hub` routes, request/response JSON schemas, HMAC-SHA256 verification headers (`X-Tracker-Signature`, `X-Tracker-Timestamp`), and HTTP status codes must remain 100% unchanged after decomposing the oversized API methods.
3. **`PluginRegistry` 12-Method Budget & Runtime Gating**:
   - `PluginRegistry` (`plugin_registry/registry.py`) is at its 12-method ceiling; `get_active_api_urlpatterns()` must be implemented as a module-level function in `plugin_registry/registry.py` and respect `PluginState` runtime gating.
4. **Security Dashboard DOM & JS Telemetry Contract (`dashboard.html`)**:
   - Decomposing `dashboard.html` into partials under `intelligent_tracker_hub/templates/intelligent_tracker_hub/partials/` must preserve all DOM IDs (`siteFilterForm`, `btnAudioChime`, `videoMatrixContainer`, `tile-{{ cam.camera_id }}`, `stream-img-{{ cam.camera_id }}`, `canvas-overlay-{{ cam.camera_id }}`, `fps-badge-{{ cam.camera_id }}`, `occupancy-badge-{{ cam.camera_id }}`), JS functions (`toggleAudioAlarm`, `toggleStreamPlay`, `toggleTileFullscreen`), and zero inline `style="..."` or `!important` rules.

---

## 4. Scenario Combinations Matrix

| Scenario ID | Milestone | Focus Area | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-501** | Milestone 1 | OpenAPI 3 Schema (`/api/v1/schema/`), Swagger UI (`/api/v1/docs/`), `AppPlugin.api_urlpatterns` & `/rest_api/` | `pytest tests/test_rest_api.py tests/test_plugin_registry.py tests/tracker/` | 100% pass; OpenAPI schema & Swagger UI return `200`; plugin API routes auto-mount under `/api/v1/` |
| **SC-502** | Milestone 2 | `django-filter`, `django-import-export` Resources/Admin & `django-htmx` List Partial Rendering | `pytest tests/crm/ tests/erp/ tests/test_home.py` | 100% pass; `FilterSet` filters queryset; `ModelResource` exports rows; `HX-Request: true` renders table partials |
| **SC-503** | Milestone 3 | Modularity Paydown (`erp/pdf.py`, `intelligent_tracker_hub/api/*.py`, `dashboard.html`) & Full Suite | `pytest tests/erp/test_invoices_and_pdf.py tests/tracker/ tests/test_intelligent_tracker_hub.py` | 100% pass; zero functions $> 40$L in target Python files; `dashboard.html` $< 350$L |
| **SC-504** | All | Full Regression Suite & Static Modularity Audit | `pytest` | 100% full test suite pass; `diagnose.py audit` passes on all Step 5 targets |

---

## 5. Multi-Phase Roadmap & Milestones

### Milestone 1: Unified `/api/v1/` (`drf-spectacular`) & `AppPlugin.api_urlpatterns` Auto-Mounting
- [x] **requirements/base.txt, enterprise_website/settings/apps.py, enterprise_website/settings/base.py & enterprise_website/settings/integrations.py**: Add `drf-spectacular`, `django-filter`, `django-import-export`, and `django-htmx` to `requirements/base.txt` (installing missing packages into `.venv`), register `drf_spectacular`, `django_filters`, `import_export`, and `django_htmx` in `THIRD_PARTY_APPS`, add `django_htmx.middleware.HtmxMiddleware` to `MIDDLEWARE`, and configure `DEFAULT_SCHEMA_CLASS`, `DEFAULT_FILTER_BACKENDS`, and `SPECTACULAR_SETTINGS` in `integrations.py`.
- [x] **plugin_registry/registry.py, rest_api/plugin.py, rest_api/v1_urls.py & enterprise_website/urls.py**: Add module-level `get_active_api_urlpatterns()` helper in `plugin_registry/registry.py` (keeping `PluginRegistry` at 12 methods), register `api_urlpatterns` on `RestApiPlugin`, create `rest_api/v1_urls.py` exposing `/api/v1/schema/`, `/api/v1/docs/`, `/api/v1/redoc/`, and active plugin API routes under `/api/v1/` alongside `intelligent_tracker_hub.api_urls` while keeping `/rest_api/` backwards-compatible.
- [x] **tests/test_rest_api.py & tests/test_plugin_registry.py**: Add unit and integration tests verifying `/api/v1/schema/` (OpenAPI 3 generation), `/api/v1/docs/` (Swagger UI), `/api/v1/users/` via `AppPlugin.api_urlpatterns`, runtime `PluginState` gating of plugin API routes, and backwards-compatible `/rest_api/users/` behavior.
- [x] **CHANGELOG.md**: Record milestone completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 2: Ecosystem Ops (`django-filter`, `django-import-export` & `django-htmx`) Across `crm`, `erp` & `location_management` (**DEFERRED TO NEXT TURN / MILESTONE**)
- [ ] **crm/resources.py, erp/resources.py, location_management/resources.py, crm/admin.py, erp/admin.py & location_management/admin.py**: Implement `ModelResource` classes for `Company`, `Contact`, `Lead`, `Product`, `Invoice`, `StockMovement`, `Countries`, `States`, `Cities`, and `Location`, and integrate `ImportExportModelAdmin` with `UnfoldModelAdmin` across `crm`, `erp`, and `location_management` admins.
- [ ] **crm/filters.py, erp/filters.py, crm/views/ & erp/views/**: Create `FilterSet` classes (`CompanyFilter`, `ContactFilter`, `LeadFilter`, `ProductFilter`, `InvoiceFilter`, `StockMovementFilter`) and wire declarative filtering plus `request.htmx` partial template rendering into `crm` and `erp` list views and templates.
- [ ] **tests/crm/, tests/erp/ & tests/test_home.py**: Add unit and integration tests verifying `FilterSet` query filtering, `ModelResource` dataset export/import in `crm`, `erp`, and `location_management`, and `HX-Request` partial rendering on list endpoints.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 3: Modularity Budget Paydown (`erp/pdf.py`, `intelligent_tracker_hub/api/*.py` & `dashboard.html`) & Final Master Roadmap Sign-Off (**DEFERRED TO NEXT TURN / MILESTONE**)
- [ ] **erp/pdf.py**: Decompose `generate_invoice_pdf` (248L) into modular ReportLab flowable helper functions (`_build_pdf_styles`, `_build_header_flowable`, `_build_bill_to_flowable`, `_build_items_flowable`, `_build_totals_flowable`, `_build_notes_and_footer_flowable`) so every function in `erp/pdf.py` is $\le 40$ lines.
- [ ] **intelligent_tracker_hub/api/access_control.py, video_evidence.py, security_events.py & video_streaming.py**: Extract single-purpose validation, authentication, media decoding, and streaming helper functions/methods so `access_control.py::post`, `video_evidence.py::post` (both classes), `security_events.py::post`, and `video_streaming.py::get`/`post` are all $\le 40$ lines and all 4 files remain $< 350$ lines.
- [ ] **intelligent_tracker_hub/templates/intelligent_tracker_hub/dashboard.html & partials/**: Decompose `dashboard.html` (630L) into a compact $< 100$L layout shell including 7 cohesive partials under `intelligent_tracker_hub/templates/intelligent_tracker_hub/partials/` while preserving all DOM IDs, JS telemetry hooks, and context bindings.
- [ ] **tests/ & .diagnostics/**: Run full regression suite (`pytest`), `diagnose.py audit` ($\le 350$L/file, $\le 40$L/fn), `diagnose.py scan --path .`, and `plan_engine.py digest --all --backfill --write-scaffold` to complete Step 5 and `platform_evolution_master_roadmap`.
- [ ] **CHANGELOG.md**: Record milestone completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.
