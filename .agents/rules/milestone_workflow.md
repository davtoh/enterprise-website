# Rule: Milestone-by-Milestone Workflow & Review

## Purpose
Prevent large, untested batches of code changes. Ensure the user can understand, manually test, and review code milestone-by-milestone before committing or advancing.

## Guidelines
1. **Incremental Scope:**
   - Group tasks into focused, self-contained milestones (e.g. Milestone 1: Routing & Navigation, Milestone 2: Auth Logic & Error Handling, etc.).
   - Do not mix unrelated architectural changes into a single milestone.
2. **Automated Verification Before Milestone Completion:**
   - Run automated checks (e.g. Django system check `manage.py check`, route status verification, unit tests, or lint checks) before closing a milestone.
3. **Structured Milestone Report:**
   - At the conclusion of every milestone, present:
     - **Summary of Changes**: What was implemented and why.
     - **Automated Test Results**: Confirmation of green checks.
     - **Manual Testing Steps**: Clear, copy-pasteable steps (URLs, user actions) for the developer to test in their browser.
     - **Pending Questions / Blockers**: Any decisions needing developer guidance.
4. **Pause for Review & Commit:**
   - Allow the user to test manually and commit their work to Git with a clean commit message when they are satisfied.
