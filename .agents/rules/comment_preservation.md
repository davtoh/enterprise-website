# Rule: Comment & Reference Preservation

## Purpose
When modernizing, refactoring, or migrating code, developer comments containing reference URLs, tutorials, architectural explanations, or historical context must NEVER be silently deleted.

## Guidelines
1. **Never Delete Reference Comments:**
   - Preserve comments containing URLs (e.g. `https://stackoverflow.com/...`, `https://docs.djangoproject.com/...`).
   - Preserve comments explaining rationale, edge cases, or tutorials (e.g. `# using next convention...`).
   - Preserve commented-out alternative implementations if they serve as reference or learning material for the developer.
2. **Annotate Rather Than Erase:**
   - If a legacy comment describes an obsolete pattern being replaced, keep the original comment or note:
     `# Legacy reference (Django 2.x): ...`
     `# Modernized (Django 5.x): ...`
3. **Preserve User Checklists & Notes:**
   - Never overwrite or clear files like `NOTES.txt`, `TODO.txt`, or legacy documentation without explicit user consent.
