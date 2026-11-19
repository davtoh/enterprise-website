# Step 4 Implementation Plan: Cross-App Composable Blocks, Public ERP Catalog & `ActionItem` Promotion

**Plan Slug:** `step_4_cross_app_blocks_and_pipelines`  
**Parent Master Plan:** `platform_evolution_master_roadmap` (Master Milestone 4)  
**Architecture Reference:** `docs/ARCHITECTURE.md` (Sections 5, 6 & 7)  
**Execution Mode:** 1-Milestone-Per-Turn Execution Gate (`plan_engine.py`)

---

## 1. Executive Summary

This child plan executes **Master Step 4** across 3 cohesive, vertically verified milestones:
1. **Milestone 1 (Composable `AppPlugin v2` Wagtail `StreamField` Blocks for `video_gallery` & `polls` + Public vs. Staff Security Video Separation — ACTIVE EXECUTION TARGET)**: Separate public showcase videos (`is_public=True`, `requires_staff=False`) from staff-only `SecurityEvent` evidence in `video_gallery`, enforce staff access checks on private evidence views/modals, and expose `VideoGalleryEmbedBlock` (`video_gallery/blocks.py`) and `PollEmbedBlock` (`polls/blocks.py`) via `AppPlugin.stream_blocks` into `CMSStreamBlock` (`StandardPage` & `BlogPage`) with theme-aware templates (`bootstrap5`, `tailwind`, `minimal`).
2. **Milestone 2 (`erp/models/` Modular Split, Public `erp.Product` Catalog & `erp.Invoice` <-> `crm` Integration — DEFERRED TO NEXT TURN / MILESTONE)**: Split `erp/models.py` (348L, at the 350L `WARN` boundary) into `erp/models/` (`__init__.py`, `catalog.py`, `invoicing.py`), add `is_published` and `public_summary` to `erp.Product` powering `/products/` and a reusable Wagtail `ProductShowcaseBlock` (`erp/blocks.py`), and add optional `crm_company` / `crm_contact` ForeignKeys on `erp.Invoice` with automatic customer field backfill while keeping plain-text customer fields 100% backwards-compatible.
3. **Milestone 3 (`todo` Promotion to Cross-App `ActionItem` via `GenericForeignKey` & `SiteUser` Locale/Timezone Sync — DEFERRED TO NEXT TURN / MILESTONE)**: Promote `todo.Todo` into a cross-app `ActionItem` model by adding optional `owner` (`SiteUser`), `status` (`ActionItemStatus`), `due_date`, and `GenericForeignKey` (`content_type`, `object_id`, `content_object`) linking to `crm.Lead` (including automatic linkage in `home/services.py`), `erp.Invoice`, and `intelligent_tracker_hub.SecurityEvent` while preserving `TodoPlugin.plugin_templates` multi-theme overrides. Sync authenticated user language (`/i18n/setlang/`) and timezone (`/tz/set/`) selections to `SiteUser.preferred_language` and `SiteUser.timezone`.

---

## 2. Quantitative Modularity & Target Budgets

| Target File | Current Lines | Planned Net Lines | Budget Status | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `video_gallery/models.py` | 239L | ~265L | **PASS** (< 350L) | Add `is_public`, `requires_staff`, and `public_videos()` helper ($\le 40$L/fn) |
| `video_gallery/views.py` | 90L | ~115L | **PASS** (< 350L) | Filter public catalog & gate `requires_staff` / `SecurityEvent` evidence |
| `video_gallery/blocks.py` | 0L (New) | ~55L | **PASS** (< 350L) | `VideoGalleryEmbedBlock` for Wagtail `StreamField` |
| `polls/blocks.py` | 0L (New) | ~50L | **PASS** (< 350L) | `PollEmbedBlock` for Wagtail `StreamField` |
| `plugin_registry/registry.py` | 170L | ~188L | **PASS** (< 350L) | Add `get_active_stream_blocks()` flattener helper |
| `cms/blocks.py` | 83L | ~110L | **PASS** (< 350L) | Integrate `video_gallery`, `poll`, and `product_showcase` blocks into `CMSStreamBlock` |
| `erp/models/__init__.py` | 348L (`models.py`) | ~35L | **PASS** (< 350L) | Package re-exports for all `erp` models and enums |
| `erp/models/catalog.py` | 0L (Split) | ~185L | **PASS** (< 350L) | `Category`, `InventoryLocation`, `Product` (`is_published`, `public_summary`), `StockMovement` |
| `erp/models/invoicing.py` | 0L (Split) | ~175L | **PASS** (< 350L) | `InvoiceStatus`, `Invoice` (`crm_company`, `crm_contact`), `InvoiceItem` |
| `erp/blocks.py` | 0L (New) | ~55L | **PASS** (< 350L) | `ProductShowcaseBlock` for Wagtail `StreamField` |
| `todo/models.py` | 20L | ~75L | **PASS** (< 350L) | `Todo` / `ActionItem` (`owner`, `status`, `due_date`, `GenericForeignKey`) |
| `todo/views.py` | 83L | ~115L | **PASS** (< 350L) | Support optional `status`, `due_date`, and `owner` filtering/creation |
| `user_management/models.py` | 99L | ~112L | **PASS** (< 350L) | Add `preferred_language` field to `SiteUser` |
| `timezone_management/views.py` | 32L | ~50L | **PASS** (< 350L) | Sync authenticated `SiteUser.timezone` on `/tz/set/` POST |
| `timezone_management/middleware.py` | 36L | ~52L | **PASS** (< 350L) | Fallback to `request.user.timezone` when session key is absent |
| `language_management/views.py` | 11L | ~45L | **PASS** (< 350L) | `set_language_and_sync_profile` view syncing `SiteUser.preferred_language` |

---

## 3. Surface Invariants & Public API Contracts

1. **Physical Security Evidence Isolation (`video_gallery` & `intelligent_tracker_hub`)**:
   - `SecurityEvent.video_evidence` (`ForeignKey("video_gallery.VideoItem", on_delete=models.SET_NULL)`) must remain unbroken.
   - Any `VideoGallery` or `VideoItem` marked `is_public=False`, `requires_staff=True`, or linked to a `SecurityEvent` must be hidden from anonymous/non-staff public gallery listings and return `404` on non-staff detail/modal requests, while remaining accessible to authenticated `is_staff=True` users.
2. **Backwards-Compatible `erp.Invoice` Customer Fields & `erp.models` Imports**:
   - Splitting `erp/models.py` into `erp/models/` must preserve all `from erp.models import Category, InventoryLocation, Product, MovementType, StockMovement, InvoiceStatus, Invoice, InvoiceItem` imports and table names.
   - `Invoice.customer_name`, `Invoice.customer_email`, and `Invoice.customer_address` remain works-out-of-the-box without requiring `crm_company` or `crm_contact`; when `crm_contact` or `crm_company` is provided and plain-text fields are blank, `Invoice.save()` auto-populates them.
3. **`todo` (`ActionItem`) & Multi-Theme `plugin_templates` Contract**:
   - `Todo.objects.create(title=..., text=...)` with only `title` and `text` must continue working with sensible defaults (`status="pending"`, `owner=None`, `due_date=None`, `content_type=None`, `object_id=None`).
   - `TodoPlugin.plugin_templates = {'bootstrap5': 'todo/bs5/', 'tailwind': 'todo/tw/'}` must remain intact and pass `tests/test_theme_management.py` and `tests/test_todo.py`.
4. **Multi-Theme & CSS `@layer` Hygiene**:
   - All new Wagtail block templates (`video_gallery_embed_block.html`, `poll_embed_block.html`, `product_showcase_block.html`) and updated templates must contain zero inline `style="..."` attributes and zero `!important` rules.

---

## 4. Scenario Combinations Matrix

| Scenario ID | Milestone | Focus Area | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-401** | Milestone 1 | Public vs. Staff `VideoGallery` Isolation & `VideoGalleryEmbedBlock` / `PollEmbedBlock` | `pytest tests/test_video_gallery.py tests/test_polls.py tests/test_cms.py tests/test_plugin_registry.py` | 100% pass; non-staff blocked from security evidence; blocks render across all 3 themes |
| **SC-402** | Milestone 2 | `erp/models/` Split, `Product.is_published`, `ProductShowcaseBlock` & `Invoice` <-> `crm` FKs | `pytest tests/erp/ tests/crm/ tests/test_home.py tests/test_cms.py` | 100% pass; `/products/` & block show published products; `Invoice` syncs from `crm` |
| **SC-403** | Milestone 3 | `Todo` (`ActionItem`) `GenericForeignKey` & `SiteUser` Language/Timezone Sync | `pytest tests/test_todo.py tests/test_home.py tests/test_timezone_management.py tests/test_user_management.py` | 100% pass; `Todo` links to `Lead`/`Invoice`/`SecurityEvent`; user prefs persist |
| **SC-404** | All | Modularity Budget & Defect Scan | `pytest tests/test_video_gallery.py tests/test_polls.py tests/test_todo.py tests/crm/ tests/erp/ tests/test_timezone_management.py tests/test_user_management.py tests/test_home.py tests/test_cms.py` | 100% pass; zero files $\ge 350$L and zero functions $> 40$L in modified modules |

---

## 5. Multi-Phase Roadmap & Milestones

### Milestone 1: Composable `AppPlugin v2` Wagtail `StreamField` Blocks (`video_gallery` & `polls`) & Public vs. Staff Video Isolation
- [x] **video_gallery/models.py, video_gallery/views.py & video_gallery/migrations/**: Add `is_public` (default `True`) and `requires_staff` (default `False`) to `VideoGallery` and `VideoItem`, add `public_videos()` queryset helper, and enforce staff-only visibility for `requires_staff=True`, `is_public=False`, or `SecurityEvent`-linked evidence in `GalleryListView`, `GalleryDetailView`, and `VideoItemModalView`.
- [x] **video_gallery/blocks.py, polls/blocks.py, video_gallery/plugin.py, polls/plugin.py, plugin_registry/registry.py & cms/blocks.py**: Implement `VideoGalleryEmbedBlock` and `PollEmbedBlock`, register them on `VideoGalleryPlugin.stream_blocks` and `PollsPlugin.stream_blocks`, add `registry.get_active_stream_blocks()`, and wire them into `CMSStreamBlock` (`StandardPage` & `BlogPage`) with migration.
- [x] **cms/templates/cms/blocks/video_gallery_embed_block.html & cms/templates/cms/blocks/poll_embed_block.html**: Create responsive, multi-theme block templates using `theme-adapter.css` semantic classes with zero inline styles and zero `!important`.
- [x] **tests/test_video_gallery.py, tests/test_polls.py & tests/test_cms.py**: Add unit and integration tests covering public vs. staff video evidence isolation, `registry.get_active_stream_blocks()`, and `VideoGalleryEmbedBlock` / `PollEmbedBlock` rendering across `bootstrap5`, `tailwind`, and `minimal`.
- [x] **CHANGELOG.md**: Record milestone completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 2: `erp/models/` Modular Split, Public `erp.Product` Catalog (`ProductShowcaseBlock`) & `erp.Invoice` <-> `crm` Integration
- [x] **erp/models/__init__.py, erp/models/catalog.py, erp/models/invoicing.py & erp/migrations/**: Split `erp/models.py` (348L) into a modular `erp/models/` package (< 200L per file), add `is_published` (default `True`) and `public_summary` to `erp.Product`, and add optional `crm_company` and `crm_contact` ForeignKeys on `erp.Invoice` with automatic customer metadata backfill in `save()`.
- [x] **erp/forms.py, erp/views/invoices.py, home/views.py & home/templates/home/products.html**: Expose `is_published`/`public_summary` on `ProductForm` and `crm_company`/`crm_contact` on `InvoiceForm`, and update `ProductsView` (`home/views.py`) and `home/products.html` to render published `erp.Product` items dynamically.
- [x] **erp/blocks.py, erp/plugin.py, cms/blocks.py & cms/templates/cms/blocks/product_showcase_block.html**: Implement `ProductShowcaseBlock`, register it on `ERPPlugin.stream_blocks`, include it in `CMSStreamBlock`, and render published ERP products with zero inline styles or `!important`.
- [x] **tests/erp/test_products_and_inventory.py, tests/erp/test_invoices_and_pdf.py, tests/test_home.py & tests/test_cms.py**: Add unit and integration tests verifying `erp.Product` public catalog filtering, `ProductShowcaseBlock` rendering across themes, and `erp.Invoice` <-> `crm.Company`/`crm.Contact` linking and customer field backfill.
- [x] **CHANGELOG.md**: Record milestone completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 3: `todo` Promotion to Cross-App `ActionItem` (`GenericForeignKey`) & `SiteUser` Locale/Timezone Sync
- [x] **todo/models.py, todo/views.py, todo/templates/todo/ & home/services.py**: Promote `Todo` (`ActionItem` alias) with `owner` (`SiteUser`), `status` (`ActionItemStatus`), `due_date`, and `GenericForeignKey` (`content_type`, `object_id`, `content_object`) linking to `crm.Lead`, `erp.Invoice`, and `intelligent_tracker_hub.SecurityEvent`, update `ingest_website_contact_submission()` (`home/services.py`) to set `content_object=lead`, and preserve `TodoPlugin.plugin_templates` multi-theme overrides.
- [x] **user_management/models.py, language_management/views.py, timezone_management/views.py, timezone_management/middleware.py & enterprise_website/urls.py**: Add `preferred_language` to `SiteUser` with migration, sync authenticated user language changes on `/i18n/setlang/` to `SiteUser.preferred_language`, and sync authenticated user timezone selections on `/tz/set/` to `SiteUser.timezone` with automatic middleware activation.
- [x] **tests/test_todo.py, tests/test_home.py, tests/test_timezone_management.py & tests/test_user_management.py**: Add unit and integration tests verifying `Todo`/`ActionItem` `GenericForeignKey` linkage across `crm.Lead`, `erp.Invoice`, and `SecurityEvent`, multi-theme `plugin_templates` rendering, and authenticated `SiteUser` language/timezone preference sync.
- [x] **CHANGELOG.md**: Record milestone completion via `python "<config_dir>/skills/system-diagnostics/scripts/diagnose.py" changelog add`.
