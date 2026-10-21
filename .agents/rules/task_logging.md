# Rule: Persistent Task & Migration Logging

## Purpose
Long-running modernization, refactoring, and multi-language migration tasks frequently span across multiple AI turns, sessions, or token/quota limits. A reliable persistent log guarantees seamless continuation without loss of context.

## Guidelines
1. **Maintain Dedicated Logs:**
   - Always maintain and update `MIGRATION_LOG.md` (and project `TODO_MODERNIZATION.md`).
   - Every significant step or task change must be recorded before proceeding to heavy edits.
2. **Standard Log Entry Structure:**
   - **Timestamp & Milestone Identifier**: e.g. `## [Milestone X] - YYYY-MM-DD`
   - **Objectives & Scope**: What is being changed and why.
   - **Files Touched**: Explicit list of files modified, created, or audited.
   - **State / Checkpoint**: Completed items, currently in-progress tasks, and next steps.
   - **Verification Instructions**: Exact manual and automated verification commands.
   - **Quota / Context Recovery Guide**: Clear state description allowing a newly spawned agent to pick up work immediately without redundant analysis.
3. **Keep Logs Atomic and Updated:**
   - Update the log at the end of each milestone or critical pivot.
