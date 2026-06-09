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
- [x] Execute Task 4: Scoring Service.
- [x] Execute Task 5: Connector Interfaces And Manual Connector.
- [x] Execute Task 6: Search Runner Persistence And Scoring Integration.
- [x] Execute Task 7: Web UI With Search, Results, And Follow-Up State.
- [x] Execute Task 8: Excel Export.
- [x] Execute Task 9: Due Diligence Card Generation.
- [x] Execute Task 10: YouTube Connector.
- [x] Execute Task 11: Search Engine Connector For Cross-Platform Candidate Links.
- [x] Execute Task 12: Queue And Worker.
- [ ] Execute Task 13: Docker Compose Deployment.

## Review
- Implementation plan saved to `docs/superpowers/plans/2026-06-03-influencer-discovery-mvp-implementation.md`.
- Verified the plan has 14 implementation tasks, required header sections, and no unfinished markers.
- Corrected an accidental write to the old workspace by moving the plan into `D:\Influencer_Discovery` and restoring the old workspace task log.
- User chose Subagent-Driven execution mode.
- Task 1 completed with spec compliance and code quality review approval. Verification: `python -m pytest -q` passed with 2 tests and one third-party FastAPI/Starlette warning; `python -m ruff check app tests` passed.
- Task 2 completed with spec compliance and code quality review approval after hardening `init_db()`, FK nullability, naive UTC defaults, and SQLite FK enforcement. Verification: `python -m pytest -q` passed with 9 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 3 completed with spec compliance and code quality review approval after hardening host validation and bidirectional multilingual expansion. Verification: `python -m pytest -q` passed with 20 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 4 completed with spec compliance and code quality review approval after preserving raw score precision and covering all-zero metrics plus per-platform normalization edge cases. Verification: `python -m pytest tests/test_scoring.py -q` passed with 5 tests; `python -m pytest -q` passed with 25 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 5 completed with spec compliance and code quality review approval. Non-blocking low review notes were accepted because they do not affect the Task 5 contract or downstream Task 6 behavior. Verification: `python -m pytest tests/test_search_runner.py -q` passed with 1 test; `python -m pytest -q` passed with 26 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 6 completed with spec compliance and code quality review approval after making candidate, contact, content, and score persistence transactional and adding failure rollback coverage. Verification: `python -m pytest tests/test_search_runner.py -q` passed with 4 tests; `python -m pytest -q` passed with 29 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 7 completed with spec compliance and code quality review approval after isolating web tests, adding missing-task 404s, redirecting failed searches to task detail, and exposing lightweight follow-up owner/status/tags/notes. Verification: `python -m pytest tests/test_web.py -q` passed with 6 tests and one third-party warning; `python -m pytest -q` passed with 33 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 8 completed with spec compliance and code quality review approval after asserting full workbook headers, adding route-level export coverage, and exporting persisted average recent views instead of a hardcoded value. Verification: `python -m pytest tests/test_exporter.py -q` passed with 3 tests and one third-party warning; `python -m pytest -q` passed with 36 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 9 completed with spec compliance and code quality review approval after adding due diligence card generation, route/template rendering, 404 guards, and blank-title fallback coverage. Verification: `python -m pytest tests/test_due_diligence.py -q` passed with 3 tests and one third-party warning; `python -m pytest -q` passed with 39 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 10 completed with spec compliance and code quality review approval after adding the dry-run-safe YouTube connector, owned-client lifecycle handling, and strict YouTube payload ID validation. Verification: `python -m pytest tests/test_youtube_connector.py -q` passed with 6 tests; `python -m pytest -q` passed with 45 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 11 completed with spec compliance and code quality review approval after adding exact host/subdomain platform classification, `youtu.be` support, lookalike host rejection, and malformed URL fallback handling. Verification: `python -m pytest tests/test_search_engine_connector.py -q` passed with 4 tests; `python -m pytest -q` passed with 49 tests and one third-party warning; `python -m ruff check app tests` passed.
- Task 12 completed with spec compliance and code quality review approval after adding RQ queue helpers, a worker entry point, inline-by-default search execution, and a queue branch that can be tested without Redis. Verification: `python -m pytest tests/test_queue.py -q` passed with 3 tests and one third-party warning; `python -m pytest -q` passed with 52 tests and one third-party warning; `python -m ruff check app tests` passed.
