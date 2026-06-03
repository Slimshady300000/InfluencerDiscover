# Influencer Discovery Implementation Planning

## Scope
- [x] Inspect migrated project context and approved design spec.
- [x] Write implementation file structure and task breakdown.
- [x] Save implementation plan to `docs/superpowers/plans/2026-06-03-influencer-discovery-mvp-implementation.md`.
- [x] Self-review implementation plan against the spec.
- [x] Ask the user to choose execution mode before implementation starts.
- [x] Execute Task 1: Project Skeleton And Dependency Setup.
- [x] Execute Task 2: Database Models And Session Helpers.
- [x] Execute Task 3: Query Parser And Multilingual Search Intent.

## Task 3 Plan

**Goal:** Add a minimal service that parses search input into a `SearchIntent` for later connector tasks.

**Files:**
- Create `tests/test_query_parser.py` with the three specified parser tests.
- Create `app/services/__init__.py` if absent.
- Create `app/services/query_parser.py` with `InputType`, `SearchIntent`, `DOMAIN_TERMS`, and parser helpers.

**TDD steps:**
- [x] Write `tests/test_query_parser.py` exactly for keyword, brief expansion, and seed URL behavior.
- [x] Run `python -m pytest tests/test_query_parser.py -q` and verify it fails because `app.services.query_parser` is missing.
- [x] Implement `app/services/__init__.py`.
- [x] Implement `app/services/query_parser.py` with URL detection, input classification, term extraction, and domain expansion.
- [x] Run `python -m pytest tests/test_query_parser.py -q` and verify it passes.
- [x] Run `python -m pytest -q`.
- [x] Run `python -m ruff check app tests`.
- [x] Self-review the diff for scope, simplicity, and Task 3 compliance.
- [x] Commit `app/services` and `tests/test_query_parser.py` with `feat: parse creator search inputs`.

## Review
- Implementation plan saved to `docs/superpowers/plans/2026-06-03-influencer-discovery-mvp-implementation.md`.
- Verified the plan has 14 implementation tasks, required header sections, and no unfinished markers.
- Corrected an accidental write to the old workspace by moving the plan into `D:\Influencer_Discovery` and restoring the old workspace task log.
- User chose Subagent-Driven execution mode.
- Task 1 completed with spec compliance and code quality review approval. Verification: `python -m pytest -q` passed with 2 tests and one third-party FastAPI/Starlette warning; `python -m ruff check app tests` passed.
- Task 2 completed with spec compliance and code quality review approval after hardening `init_db()`, FK nullability, naive UTC defaults, and SQLite FK enforcement. Verification: `python -m pytest -q` passed with 9 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 3 completed with the specified TDD red/green parser coverage and minimal service implementation. Verification: `python -m pytest tests/test_query_parser.py -q` passed with 3 tests; `python -m pytest -q` passed with 12 tests and one third-party FastAPI/Starlette warning; `python -m ruff check app tests` passed.
