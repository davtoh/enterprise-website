# Enterprise Multi-Theme Architecture & Layout Contract

## 1. Architectural Overview

Enterprise Website runs three switchable frontend themes—`bootstrap5` (Bootstrap 5.3.3), `tailwind` (Tailwind CSS Play CDN + Alpine.js), and `minimal` (Minimal Semantic CSS)—on top of a single shared set of Django domain templates (`crm/`, `erp/`, `todo/`, `polls/`, `home/`, `task_runner/`, `video_gallery/`, `user_management/`).

Instead of duplicating 50+ templates per CSS framework, the architecture enforces a **Hybrid Component & Layout Contract** backed by formal **CSS Cascade Layers (`@layer`)**:

1. **Theme Shell (`templates/themes/<theme>/`)**: Framework-specific `base.html` and chrome partials (`partials/header.html`, `partials/footer.html`, `partials/messages.html`, `partials/styles.html`, `partials/scripts.html`, `partials/theme_selector.html`).
2. **Shared Domain Templates**: App views extend `base.html` and emit framework-agnostic layout classes (`.container`, `.container-fluid`, `.row`, `.col-*`, `.card`, `.list-group`, `.btn`, `.btn-primary`) plus brand tokens from `static/css/theme-tokens.css`.
3. **Zero-Dependency Adapter (`static/css/theme-adapter.css`)**: Supplies grid, container, card, list-group, and utility classes inside `@layer adapter` and `@layer utilities` so Tailwind and Minimal themes render Bootstrap-compatible shared templates with visual parity.

---

## 2. Theme Resolution & Template Loading

### Request Resolution Precedence (`theme_management/middleware.py`)
`ThemeMiddleware` resolves the active theme into thread-local storage (`set_current_theme`) and `request.site_theme` in strict priority order:
1. Query parameter: `?theme=<name>` (validated against `settings.AVAILABLE_THEMES`; persists to session and `site_theme` cookie).
2. User session: `request.session['site_theme']`.
3. Persistent cookie: `request.COOKIES['site_theme']`.
4. Global setting fallback: `settings.SITE_THEME` (default `'bootstrap5'`, configured in `enterprise_website/settings/base.py`).

### Template Resolution (`theme_management/loaders.py`)
`ThemeTemplateLoader` resolves templates in order before falling back to `filesystem.Loader` and `app_directories.Loader`:
1. Plugin overrides from `AppPlugin.plugin_templates` (e.g., `todo/plugin.py` maps `bootstrap5 -> todo/bs5/` and `tailwind -> todo/tw/`).
2. Active theme directory: `templates/themes/<current_theme>/<template_name>`.
3. Shared root templates: `templates/<template_name>`.

### Interactive Switching Endpoints (`theme_management/urls.py`)
- `GET /theme/set/<theme_name>/` (`theme_management:set_theme`)
- `POST /theme/set/` (`theme_management:set_theme_form`)
Both validate redirect targets via `url_has_allowed_host_and_scheme` (`theme_management/views.py`) to block open redirects.

---

## 3. CSS Cascade Layers (`@layer`) & Container Parity

All themes share an explicit cascade order declared in `static/css/theme-tokens.css`, `static/css/theme-adapter.css`, and `templates/themes/bootstrap5/partials/styles.html`:

```css
@layer tokens, framework, adapter, components, utilities;
```

| Layer | Purpose | Primary Sources |
| :--- | :--- | :--- |
| `tokens` | CSS custom properties (brand palette, semantic colors, shadows, radii, container vars) | `static/css/theme-tokens.css`, `templates/themes/minimal/partials/styles.html` |
| `framework` | Base framework CSS and resets | Bootstrap 5.3.3 + `static/css/main.css`, Tailwind Preflight/compat block, Minimal base rules |
| `adapter` | Cross-framework `.container`, `.container-fluid`, `.row`, `.col-*`, `.card`, `.list-group` | `static/css/theme-adapter.css`, Minimal `.container` override |
| `components` | Brand UI components (`.btn-brand-primary`, `.btn-hero-cta`, `.card-brand`, `.navbar-brand-theme`) | `static/css/theme-tokens.css`, `static/css/django.css` |
| `utilities` | Gutters (`.g-0`..`.g-5`), subtle badges, directional borders, spacing, flex, display | `static/css/theme-adapter.css` |

### Container Centering Contract
- `static/css/theme-adapter.css` defines `.container`, `.container-fluid`, and `.container-{sm,md,lg,xl,xxl}` inside `@layer adapter` with `box-sizing: border-box`, `width: 100%`, `margin-inline: auto`, `--bs-gutter-x: var(--container-gutter-x, 1.5rem)`, `padding-inline: calc(var(--bs-gutter-x) * 0.5)`, and responsive max-widths (`540px`, `720px`, `960px`, `1140px`, `1320px`).
- `templates/themes/tailwind/partials/styles.html` sets `tailwind.config.theme.container = { center: true, padding: '1rem' }` and disables unlayered preflight (`corePlugins: { preflight: false }`) so Tailwind utilities compose cleanly with `@layer adapter`.
- `templates/themes/minimal/partials/styles.html` sets `--container-max-width: 1200px` and `--container-gutter-x: 2rem` in `@layer tokens` and aligns `.container` in `@layer adapter`.

---

## 4. Zero `!important` Hygiene Policy

Application CSS (`static/css/theme-tokens.css`, `static/css/theme-adapter.css`, `static/css/main.css`, `static/css/django.css`, app static stylesheets, and `<style>` blocks in `templates/themes/*/partials/styles.html`) **MUST NOT** contain `!important`. Resolve specificity conflicts using `@layer` ordering or scoped selectors.

**Allowed Exceptions Only:**
- Third-party vendor stylesheets (`static/css/bootstrap.css`, `magnific-popup.css`, `nice-select.css`, `animate.min.css`, `font-awesome.min.css`, `linearicons.css`).
- Framework FOUC protocol directives (`[x-cloak] { display: none !important; }` for Alpine.js).
- Email client HTML compatibility styles (`crm/tasks.py`, `crm/utils.py`).

---

## 5. Developer Guidelines for Adding New Views

When building a new Django app or view template:
1. **Extend `base.html`**: Never hardcode a theme path (`templates/themes/bootstrap5/base.html`); extend `"base.html"` so `ThemeTemplateLoader` selects the active theme dynamically.
2. **Use Standard Container Wrappers**: Wrap page content inside `{% block content %}` with `<div class="container">` (standard views like `todo/templates/todo/index.html`) or `<div class="container-fluid py-4 px-md-4">` (wide dashboards like `crm/templates/crm/base_crm.html`). Never add `mx-0`, `ml-0`, `mr-0`, `ms-0`, `me-0`, or inline `margin-left: 0` on containers.
3. **Stick to the Contracted Class Set**: Prefer `.row`, `.col-*`, `.g-*`, `.card`, `.card-header`, `.card-body`, `.list-group`, `.btn`, `.btn-primary`, `.btn-brand-primary`, and `.bg-*-subtle` supported by both Bootstrap 5.3 and `theme-adapter.css`.
4. **Zero Inline Styles & Clean Icons**: Avoid `style="..."` attributes (except dynamic bindings such as progress bar widths) and always prefix FontAwesome 4.x icons with `fa fa-<name>`.
5. **Internationalization**: Load `{% load i18n %}` and wrap user-facing strings with `{% trans %}` / `{% blocktrans %}`.
6. **Verify Across All Themes**: Add your route to theme parity checks and run the automated CSS hygiene and container DOM tests before merging.

---

## 6. 1-Step Decoupling Recipe (Single-Framework Consolidation)

If you decide in the future to standardize on a single CSS framework (for example `bootstrap5` or `tailwind`) and retire runtime theme switching:

1. **Pin the Default Theme**: Set `AVAILABLE_THEMES = ['bootstrap5']` and `SITE_THEME = 'bootstrap5'` in `enterprise_website/settings/base.py` (or restrict `SITE_THEME` via `.env`).
2. **Optional Full Removal**:
   - Copy `templates/themes/<chosen_theme>/*` directly into `templates/`.
   - Remove `'theme_management.middleware.ThemeMiddleware'`, `'theme_management.loaders.ThemeTemplateLoader'`, and `'theme_management.context_processors.theme_context'` from `enterprise_website/settings/base.py`.
   - Remove `path('theme/', include('theme_management.urls'))` from `enterprise_website/urls.py` and the theme switcher include from `partials/header.html`.
   - If consolidating on `tailwind` or `minimal`, retain `static/css/theme-tokens.css` and `static/css/theme-adapter.css` (or convert incrementally); **zero domain templates** in `crm/`, `erp/`, `todo/`, `polls/`, `home/`, `task_runner/`, `video_gallery/`, or `user_management/` need rewrites to remain functional.

---

## 7. Pre-Run Verification & Scenario Matrix

### Quick Pre-Run Checks
```bash
python manage.py check
pytest tests/test_theme_management.py -v
```

### Scenario Combinations Matrix

| Scenario # | Theme Context | Target / Scope | Expected Behavior | Runnable Command |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | `bootstrap5` | `crm/dashboard.html` & `todo/index.html` | Centered containers with `@layer framework` + `theme-adapter.css` (`max-width: 1320px`) | `pytest tests/test_theme_management.py -k test_container` |
| **S2** | `tailwind` | `crm/dashboard.html` & `todo/index.html` | Centered containers via `tailwind.config.theme.container.center = true` + `@layer adapter` | `pytest tests/test_theme_management.py -k test_container` |
| **S3** | `minimal` | `crm/dashboard.html` & `todo/index.html` | Centered containers via `--container-max-width: 1200px` and `margin-inline: auto` | `pytest tests/test_theme_management.py -k test_container` |
| **S4** | All Themes | Application CSS & theme `<style>` blocks | Zero `!important` outside vendor CSS and `[x-cloak]` | `pytest tests/test_theme_management.py -k test_zero_important` |
| **S5** | Regression | Django app unit tests & full pytest suite | 100% passing with zero regressions | `python manage.py test && pytest` |

