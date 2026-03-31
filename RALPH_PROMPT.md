# ContraRed Implementation — Ralph Loop Prompt

You are implementing the ContraRed Next Features roadmap. You work autonomously, one task at a time, with strict quality gates.

## YOUR FILES

1. **PLAN:** `docs/plans/2026-03-31-contrared-next-features.md` — the full feature specifications, DB schemas, code examples, and architecture
2. **CHECKLIST:** `RALPH_CHECKLIST.md` — your task list with status tracking
3. **LOG:** `RALPH_LOOP_LOG.md` — append a log entry after every task
4. **REGRESSION TESTS:** `backend/tests/test_regression.py` — 14 baseline regression tests that must ALWAYS pass

## ITERATION PROTOCOL

Every iteration, do exactly this:

### Step 1: READ STATE
```
Read RALPH_CHECKLIST.md
```
Find the FIRST task with status `NOT_DONE`. This is your current task.
- If all tasks are `DONE`, output `<promise>ALL FEATURES IMPLEMENTED</promise>` and stop.
- Note the CURRENT_TASK field at the top of the checklist.

### Step 2: READ PLAN (if needed)
```
Read docs/plans/2026-03-31-contrared-next-features.md
```
Find the section matching your current task. Use the DB schemas, code examples, and architecture from the plan. Do NOT invent new approaches — follow the plan exactly.

### Step 3: IMPLEMENT THE TASK
- Implement ONLY the current task. Do not skip ahead.
- Follow the plan's code examples and schemas closely.
- Preserve ALL existing behavior (backwards compatible).
- Do NOT modify existing tests (only ADD new ones).
- Do NOT delete or rename existing functions/classes/endpoints.
- When creating new files, follow existing patterns in the codebase.
- When editing files, make minimal changes — only what the task requires.

### Step 4: RUN QUALITY GATES (MANDATORY — NEVER SKIP)

Run these commands IN ORDER. If ANY fail, fix before proceeding:

```bash
# Gate 1: App imports clean
cd backend && python -c "from main import app; print('IMPORT OK')"

# Gate 2: Regression tests (MUST be 14/14 pass)
cd backend && python -m pytest tests/test_regression.py -v --tb=short

# Gate 3: Full test suite (ALL must pass)
cd backend && python -m pytest tests/ -v --tb=short

# Gate 4: New test (if task created one)
cd backend && python -m pytest tests/test_NEW_FILE.py -v --tb=short
```

**CRITICAL RULES:**
- If Gate 1 fails: you broke an import. Fix it immediately.
- If Gate 2 fails: you broke existing functionality. REVERT your changes and try again.
- If Gate 3 fails: investigate. If it's your new test failing, fix the implementation. If it's an old test, you introduced a regression — fix it.
- NEVER mark a task DONE if any gate fails.
- NEVER skip gates to "save time."
- NEVER modify test_regression.py to make it pass.

### Step 5: UPDATE CHECKLIST
Edit `RALPH_CHECKLIST.md`:
- Change the task's `**STATUS:** NOT_DONE` to `**STATUS:** DONE`
- Check all the `- [ ]` boxes for the task: change to `- [x]`
- Update `CURRENT_TASK:` at the top to the NEXT task ID
- If completing a checkpoint (e.g., S1-F1-CHECKPOINT), update `CURRENT_SPRINT` too

### Step 6: UPDATE LOG
Append to `RALPH_LOOP_LOG.md`:
```markdown
### Iteration N — TASK_ID
**Action:** Brief description of what was implemented
**Files Changed:** list of files
**Tests:** X/Y passed (Y total)
**Quality Gate:** PASS
**Next Task:** next task ID
```

### Step 7: GIT COMMIT
```bash
git add -A
git commit -m "feat(FEATURE): TASK_ID — brief description"
```

Use appropriate commit prefixes:
- `feat(compliance):` for DPDP/compliance layer tasks
- `feat(source-trail):` for source trail tasks
- `feat(batch):` for batch upload tasks
- `feat(learning):` for institutional memory tasks
- `feat(jurisdiction):` for jurisdiction engine tasks
- `feat(marketplace):` for marketplace tasks
- `feat(agent):` for agentic AI tasks
- `feat(smriti):` for Smriti MCP tasks
- `test:` for test-only tasks

### Step 8: DECIDE NEXT
- If this was a checkpoint task, note sprint completion.
- Move to the next NOT_DONE task.
- If you've been working for a while and want to stop, output: `<promise>ALL FEATURES IMPLEMENTED</promise>`

## SAFETY RULES

1. **ONE TASK PER ITERATION.** Do not bundle tasks.
2. **TESTS FIRST, CODE SECOND.** If the task is "Write tests for X", write the tests. If the task is "Implement X", write the code AND make sure tests pass.
3. **BACKWARDS COMPATIBLE.** Never break existing API contracts. New fields must be optional with defaults.
4. **NO DESTRUCTIVE CHANGES.** Never delete tables, columns, endpoints, or functions that existing code depends on.
5. **FOLLOW EXISTING PATTERNS.** Look at how existing models, services, and endpoints are structured. Match the style.
6. **GRACEFUL DEGRADATION.** New features (Smriti, compliance layers) must be optional. The system works without them.
7. **MINIMAL CHANGES.** Only change what the task requires. Don't refactor, clean up, or "improve" surrounding code.

## FAILURE RECOVERY

If you find yourself stuck:
1. Read the error message carefully
2. Read the file that's failing
3. Check if you introduced a circular import
4. Check if a model is missing from __init__.py
5. Check if a migration references a table that doesn't exist in test DB
6. Log the failure in RALPH_LOOP_LOG.md with full error text
7. Fix and retry — do NOT skip the task

If you've tried 3 times and can't fix it:
1. Revert your changes: `git checkout -- .`
2. Log: "BLOCKED on TASK_ID — [reason]"
3. Move to next task and come back later

## CONTEXT: EXISTING CODEBASE

- **Backend:** FastAPI, SQLAlchemy async, PostgreSQL (SQLite for tests)
- **Models:** `backend/app/models/` — User, Document, Playbook, Organization, etc.
- **Services:** `backend/app/services/` — AnalysisPipeline, GeminiAnalyzer, JurisdictionDetector, etc.
- **Endpoints:** `backend/app/api/v1/endpoints/` — auth, documents, playbooks, billing, etc.
- **Tests:** `backend/tests/` — pytest + pytest-asyncio, in-memory SQLite
- **Test DB:** SQLite with PostgreSQL type remapping (JSONB→JSON, ARRAY→JSON, UUID→String)
- **Baseline:** 35 tests, ALL passing

## START

Read `RALPH_CHECKLIST.md` now and begin the first NOT_DONE task.
