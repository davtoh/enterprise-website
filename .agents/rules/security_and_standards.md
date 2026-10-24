# Rule: Security & Engineering Standards

## Purpose
Enforce industry-standard best practices, OWASP Top 10 guidelines, 12-factor application methodology, and language/framework conventions across all project modernizations and migrations.

## Guidelines
1. **Security First (OWASP & Framework Standards):**
   - **Secrets & Infrastructure Isolation**: 
     - Never commit API keys, database passwords, tokens, or `SECRET_KEY` in source control. Always utilize `.env` files and environment variables. Provide `.env.example` templates.
     - **Zero Hardcoded Infrastructure Details**: Never embed connection strings (e.g. `redis://...`, `postgres://...`), hostnames/IPs (`127.0.0.1`, `localhost`), credentials, or port numbers (`6379`, `5432`, `3306`, etc.) as hardcoded fallback literals in Python code or configuration dictionaries.
     - All infrastructure endpoints, ports, passwords, and external services must resolve strictly from environment variables (`os.getenv(...)`) with safe empty-string fallbacks (`""`) or explicit configuration errors.
   - **Safe Database Queries**: Never use raw string formatting in SQL queries. Always use ORM parameterization to prevent SQL injection.
   - **XSS & Template Escaping**: Rely on framework auto-escaping in templates; avoid bypassing safe tags (`|safe`) unless strictly required and sanitized.
   - **CSRF & Form Security**: Ensure all state-changing operations (POST, PUT, DELETE) include CSRF protection.
   - **Authentication & Authorization**: Verify permissions and authentication state on all protected views. Use framework built-in hashing and token generators.
   - **Error Handling**: Replace hard-crashing `.objects.get()` with safe lookups like `get_object_or_404()` to avoid leaking uncaught 500 stack traces.
2. **Cross-Platform Compatibility:**
   - Code must run seamlessly across Windows (PowerShell/CMD), Linux (bash), and macOS (zsh).
   - Use `pathlib.Path` or `os.path` for path manipulation; never hardcode POSIX (`/`) or Windows (`\`) slashes in filesystem operations.
3. **Idiomatic Style:**
   - Adhere to PEP 8 in Python (and standard idioms in other languages when migrating).
   - Use meaningful variable and function names.
   - Keep views, models, and controllers modular and single-responsibility.
