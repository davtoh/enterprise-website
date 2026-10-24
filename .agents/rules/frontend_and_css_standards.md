# Frontend, CSS & UI Framework Guidelines

To ensure visual consistency, functional interactive components, and clean DevOps isolation across this project, all AI assistants and developers must adhere to the following standards:

---

## 1. CSS Framework Baseline & Custom Style Elimination Policy
- **Legacy State (Bootstrap 4.x / 3.x mix):** The legacy layout uses `static/css/bootstrap.css` (Bootstrap 4.0.0-beta) and `scripts.html` (Bootstrap 3.3.7 JS).
- **Modernization & Custom Style Elimination Rule:**
  - Whenever templates are created, edited, or modernized (Milestone 12+), **eliminate all custom inline styles** (`style="margin-right: ...;"`, `style="display: flex;"`, `style="z-index: ...;"`) and custom modal CSS overrides (`#launchTaskModal.show`, manual backdrop styling).
  - Use native framework utility classes exclusively:
    - Replace margin/flex hacks with native Bootstrap 5 spacing and flex utilities (`me-2`, `ms-2`, `gap-2`, `d-flex`).
    - Standardize interactive triggers exclusively on native `data-bs-*` attributes (`data-bs-toggle="modal"`, `data-bs-target`, `data-bs-dismiss="modal"`).
  - No new ad-hoc custom CSS classes or `<style>` blocks should be introduced into application templates; layout and styling must strictly use standard design system utility classes.

---

## 2. Icon Font Standards (FontAwesome 4.x)
- **Primary Icon Library:** The project uses **FontAwesome 4.3** at `static/css/font-awesome.min.css`.
- **Mandatory `fa` Prefix:**
  - FontAwesome 4 requires the base class `fa` together with the icon class:
    ```html
    <!-- Correct -->
    <i class="fa fa-tasks"></i>
    <i class="fa fa-cogs"></i>
    <i class="fa fa-check-circle"></i>

    <!-- INCORRECT (Renders empty square box glyph) -->
    <i class="fa-tasks"></i>
    <i class="fas fa-tasks"></i>
    ```
  - When registering menu items in `plugin.py`, always provide `icon="fa fa-<name>"`.

---

## 3. Interactive Components & Modals (Cross-Version Data Attributes)
- **Modal and Dropdown Data APIs:**
  - To prevent JavaScript breakages across Bootstrap 3/4 and modern Bootstrap 5 bundles, interactive UI triggers must specify **both** legacy and modern data attributes:
    ```html
    <button type="button" 
            class="btn btn-primary"
            data-toggle="modal" 
            data-bs-toggle="modal" 
            data-target="#myModal" 
            data-bs-target="#myModal">
      Open Modal
    </button>
    ```
  - Dismiss buttons must include both `data-dismiss="modal"` and `data-bs-dismiss="modal"`.
  - Include defensive vanilla JavaScript or jQuery fallbacks on custom modals to guarantee trigger response even if the data-api event listeners are delayed.

---

## 4. Docker Ports & Network Security
- **Production Isolation (`docker-compose.yml`):**
  - Production compose definitions must **never** expose internal database (PostgreSQL 5432, MySQL 3306) or in-memory cache/broker (Redis 6379) ports to the host interface.
  - Internal services must communicate exclusively over the isolated internal Docker bridge network (`enterprise_network`).
- **Local Developer Overrides (`docker-compose.override.yml`):**
  - Host port forwarding (e.g. `"${REDIS_PORT:-6379}:6379"`, `"${POSTGRES_PORT:-5432}:5432"`) belongs strictly in `docker-compose.override.yml`.
  - Docker Compose automatically layers `docker-compose.override.yml` on top of `docker-compose.yml` for local CLI, GUI clients (DBeaver, Redis Insight), and native OS test runners.
  - Keep sensitive or machine-specific overrides out of production commits; maintain `docker-compose.override.yml.example` as a template for developers.

---

## 5. Database Schema & Auto-Field Integrity
- **Primary Key Consistency (`DEFAULT_AUTO_FIELD`):**
  - To match the legacy database schema and prevent cascading foreign key type mismatch errors, `DEFAULT_AUTO_FIELD` must remain `django.db.models.AutoField` (or explicitly migrated with coordinated FK migrations).
  - Model identifiers (e.g., `task_id`, `slug`, `uuid`) with `unique=True` constraints must always provide a non-null default generator (e.g. `default=generate_task_id` or `default=uuid.uuid4`) and use `get_or_create` / `update_or_create` to ensure idempotent insertions.
