# Rule: Internationalization (i18n) & Rosetta Translation Standards

## Purpose
Ensure all user-facing content across templates, views, forms, and models is systematically prepared for multi-language support (i18n) and compatible with `django-rosetta` and Django translation catalogs (`makemessages` / `compilemessages`).

## Core Guidelines

1. **Templates Translation (`{% trans %}` / `{% blocktrans %}`):**
   - Every Django HTML template containing user-visible text must load the i18n library at the top:
     ```html
     {% load i18n %}
     ```
   - Short text, titles, navigation links, and button labels must use `{% trans "Text" %}` or `{% translate "Text" %}`:
     ```html
     <a href="{% url 'home:about' %}">{% trans "About Us" %}</a>
     <button type="submit">{% trans "Save" %}</button>
     ```
   - Content with variables or formatting must use `{% blocktrans %}` / `{% blocktranslate %}`:
     ```html
     {% blocktrans with name=user.username %}Welcome back, {{ name }}!{% endblocktrans %}
     ```
   - Form field labels, placeholders, and error badges should always expose translated text.

2. **Python Code Translation (`gettext_lazy` / `gettext`):**
   - In models and forms, always import and use lazy translation:
     ```python
     from django.utils.translation import gettext_lazy as _
     ```
     Apply it to `verbose_name`, `verbose_name_plural`, `help_text`, and form field labels:
     ```python
     title = models.CharField(_("Title"), max_length=200)
     ```
   - In views and utility functions evaluated per request (such as flash messages), use `gettext` or `gettext_lazy`:
     ```python
     from django.utils.translation import gettext as _
     messages.success(request, _("Your changes have been saved successfully."))
     # Variable interpolation:
     messages.success(request, _("Welcome, %(name)s!") % {"name": user.username})
     ```

3. **Rosetta & Locale Catalog Integration:**
   - Always verify that all target languages configured in `LANGUAGES` within `settings.py` (e.g. `es`, `fr`, `it`, `ja`, `pt`) have matching directories under `locale/`.
   - Ensure `django.template.context_processors.i18n` is active in `TEMPLATES` context processors.
   - When introducing or altering strings, keep string syntax clean and unambiguous so `manage.py makemessages --all --ignore=.venv` can extract all tokens without syntax errors.
   - Run `makemessages` and `compilemessages` whenever templates or messages are updated.

4. **Automated & Continuous Translation Workflow:**
   - Support automated baseline translation tools (such as batch machine translation scripts or Rosetta translation suggestions) to populate initial `.po` files.
   - Maintain human-editable PO catalogs so translations can be refined and corrected via `/rosetta/` or directly in PO files.
   - Never remove translator comments, obsolete flags, or existing manual translations in `.po` files without explicit developer intent.
