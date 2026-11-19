# Step 1 Implementation Plan: Security, Dead-Code & Hygiene Hardening + Lead Intake Pipeline

**Plan Slug:** `step_1_security_hygiene_hardening`  
**Parent Master Plan:** `platform_evolution_master_roadmap` (Master Milestone 1)  
**Architecture Reference:** `docs/ARCHITECTURE.md` (Section 2 & Section 7)  
**Execution Mode:** 1-Milestone-Per-Turn Execution Gate (`plan_engine.py`)

---

## 1. Executive Summary

This child plan executes **Master Step 1** across 3 atomic, vertically verified milestones:
1. **Milestone 1 (REST API Security, Structure & Secret Hygiene)**: Fix the HIGH-severity anonymous PII exposure on `/rest_api/users/` (`UserViewSet`), split serializers and viewsets out of `rest_api/urls.py` into `rest_api/serializers.py` and `rest_api/views.py`, remove the literal Google Maps API key comment from `templates/partials/scripts.html`, and enforce explicit production secret validation when `DEBUG=False`.
2. **Milestone 2 (Dead-Code Pruning, i18n Fixes & URL Namespace Parity)**: Remove dead/broken views (`user_management.views.upload_pic`, `webprogram.views.index2`), wrap `webprogram` title in `gettext_lazy`, add `app_name = "timezone_management"` with backwards-compatible URL reversal, decouple `custom_tags/templatetags/present.py` by moving `show_results` into `polls/templatetags/poll_tags.py` (retaining a 1-line delegate in `present.py`), and clean up unused imports in `language_management/views.py` and `enterprise_website/urls.py`.
3. **Milestone 3 (Home Contact-to-CRM Lead & Follow-Up Intake Pipeline)**: Fix `home.views.ContactView.post` dropping user inquiries by creating/updating a `crm.Contact`, recording a `crm.Lead` (`source=LeadSource.WEBSITE`) + `crm.InteractionLog`, and generating a follow-up `todo.Todo` action item.

---

## 2. Quantitative Modularity & Target Budgets

| Target File | Current Lines | Planned Net Lines | Budget Status | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| `rest_api/serializers.py` | 0L (New) | ~40L | **PASS** (< 350L) | `UserSerializer` with dynamic `?val=` field filtering |
| `rest_api/views.py` | 3L | ~30L | **PASS** (< 350L) | `UserViewSet` with `IsAuthenticated` & self/staff queryset scoping |
| `rest_api/urls.py` | 58L | ~20L | **PASS** (< 350L) | DRF `DefaultRouter` wiring only |
| `templates/partials/scripts.html` | 35L | ~25L | **PASS** (< 350L) | Script includes with literal API key comment removed |
| `enterprise_website/settings/base.py` | 160L | ~168L | **PASS** (< 350L) | Production `SECRET_KEY` guard when `DEBUG=False` |
| `user_management/views.py` | 205L | ~192L | **PASS** (< 350L) | Auth & profile views with dead `upload_pic` removed |
| `webprogram/views.py` | 21L | ~18L | **PASS** (< 350L) | `HomeView` with `gettext_lazy` title and dead `index2` removed |
| `timezone_management/urls.py` | 6L | ~8L | **PASS** (< 350L) | Namespace `app_name = 'timezone_management'` |
| `home/services.py` | 0L (New) | ~55L | **PASS** (< 350L) | `ingest_website_contact_submission` service ($\le 40$L fn) |
| `home/views.py` | 76L | ~72L | **PASS** (< 350L) | Public views delegating contact POST to `home.services` |

---

## 3. Surface Invariants & Public API Contracts

1. **REST API Contract (`rest_api`)**:
   - `GET /rest_api/` (`rest_api:api-root`) remains publicly reachable (`200 OK`).
   - `GET /rest_api/users/` (`rest_api:siteuser-list`) and `GET /rest_api/users/<pk>/` (`rest_api:siteuser-detail`) require authentication (`401`/`403` for anonymous callers).
   - Authenticated staff (`is_staff=True`) can list/inspect all users and filter fields via `?val=username&val=email`; authenticated non-staff users only see their own `SiteUser` record.
2. **Timezone URL Reversal Compatibility**:
   - Both `reverse('timezone_management:set_timezone')` and legacy `reverse('set_timezone')` (or updated template/test callers) must resolve `/tz/set/` without `NoReverseMatch`.
3. **Contact Form UX Contract**:
   - `POST /contact/` with valid `name`, `email`, `subject`, `message` still redirects (`302` $\to$ `200`) and flashes the translated success message containing the sender's name (`tests/test_home.py`), while atomically persisting `crm.Contact`, `crm.Lead`, and `todo.Todo`.

---

## 4. Scenario Combinations Matrix

| Scenario ID | Milestone | Focus Area | Verification Command | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **SC-101** | Milestone 1 | REST API Auth & Dynamic Fields | `pytest tests/test_rest_api.py` | Anonymous `/rest_api/users/` rejected (`403`); authenticated staff & self queries pass |
| **SC-102** | Milestone 1 | Secret Hygiene Scan | `git grep -n "AIzaSy" templates/` | Exit code 1 (zero hardcoded API keys in `templates/`) |
| **SC-103** | Milestone 2 | Timezone, Polls, WebProgram & User Views | `pytest tests/test_timezone_management.py tests/test_polls.py tests/test_webprogram.py tests/test_user_management.py` | 100% pass; zero dead views or broken template tags |
| **SC-104** | Milestone 3 | Contact-to-CRM Lead & Follow-Up Intake | `pytest tests/test_home.py tests/crm/` | Contact POST creates `crm.Contact`, `crm.Lead` (`website`), and follow-up `todo.Todo` |
| **SC-105** | All | Modularity & Full Regression Suite | `pytest` | All 381+ tests pass; `diagnose.py audit` reports 0 budget violations |

---

## 5. Multi-Phase Roadmap & Milestones

### Milestone 1: REST API Permission Lockdown, Serializer Separation & Secret Hygiene (**ACTIVE EXECUTION TARGET**)
- [x] **rest_api/serializers.py**: Create `UserSerializer` (extracted from `rest_api/urls.py`) preserving dynamic `?val=` query-param field filtering and `rest_api:siteuser-detail` hyperlinked identity.
- [x] **rest_api/views.py**: Implement `UserViewSet` with `permission_classes = [permissions.IsAuthenticated]` and `get_queryset()` scoping full queryset to `is_staff=True` and `User.objects.filter(pk=request.user.pk)` for standard authenticated users.
- [x] **rest_api/urls.py**: Slim `rest_api/urls.py` to import `UserViewSet` from `rest_api.views` and register `router.register(r'users', UserViewSet, basename='siteuser')`.
- [x] **templates/partials/scripts.html & enterprise_website/urls.py**: Remove the commented legacy block containing the literal Google Maps API key in `templates/partials/scripts.html` and prune unused DRF imports from `enterprise_website/urls.py`.
- [x] **tests/test_rest_api.py**: Add `test_users_list_requires_authentication` (asserting `403` for anonymous `GET`), update existing list/detail/dynamic-field tests to authenticate via `api_client.force_authenticate`, and test non-staff self-scoping.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 2: Dead-Code Pruning, i18n Fixes & URL Namespace Standardization (**DEFERRED TO NEXT TURN / MILESTONE**)
- [x] **user_management/views.py**: Remove the unrouted, broken `upload_pic` function (lines 193–205) and clean any unused imports in `user_management/views.py`.
- [x] **webprogram/views.py & language_management/views.py**: Wrap `HomeView` title in `gettext_lazy` (`_("Brython WebProgram")`), delete dead `index2` function in `webprogram/views.py`, and remove the unused `from utils import get_referer_view` import in `language_management/views.py`.
- [x] **timezone_management/urls.py & templates/ & tests/test_timezone_management.py**: Add `app_name = 'timezone_management'` in `timezone_management/urls.py`, keep a root fallback alias or update `timezone_management/templates/timezone_management/select.html` and `tests/test_timezone_management.py` to support `'timezone_management:set_timezone'`.
- [x] **polls/templatetags/poll_tags.py & custom_tags/templatetags/present.py**: Extract `show_results` into `polls/templatetags/poll_tags.py`, delegate `custom_tags/templatetags/present.py` to it while pruning the 11 unused imports in `present.py`, and verify with `pytest tests/test_polls.py tests/test_timezone_management.py tests/test_webprogram.py tests/test_user_management.py`.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.

### Milestone 3: Home Contact-to-CRM Lead & Follow-Up Intake Pipeline (**DEFERRED TO NEXT TURN / MILESTONE**)
- [x] **home/services.py**: Create `ingest_website_contact_submission(name, email, subject, message)` that atomically `update_or_create`s `crm.Contact`, creates a `crm.Lead` (`source=LeadSource.WEBSITE`) + `crm.InteractionLog`, and creates a follow-up `todo.Todo` record.
- [x] **home/views.py**: Wire `ContactView.post` to call `ingest_website_contact_submission` when `name`, `email`, and `message` are valid, and prune unused imports in `home/views.py` and `home/models.py`.
- [x] **tests/test_home.py**: Expand `test_contact_form_submission_success` (and add dedicated assertions) verifying that submitting `/contact/` creates `crm.Contact`, `crm.Lead` (`LeadSource.WEBSITE`), and a follow-up `todo.Todo` item.
- [x] **CHANGELOG.md**: Record milestone completion via `python "C:/Users/User/.gemini/config/skills/system-diagnostics/scripts/diagnose.py" changelog add`.
