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
- [x] Execute Task 13: Docker Compose Deployment.
- [x] Execute Task 14: End-To-End Verification.
- [x] Execute Task 15: Multi-Platform Candidate Discovery Remediation.
- [x] Execute Task 16: Manager-Usable Candidate Table Remediation.
- [ ] Execute Task 17: Internal Access Guardrails Remediation.
- [ ] Execute Task 18: Excel Formula Injection Guard Remediation.
- [ ] Execute Task 19: Final Remediation Verification And Review.

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
- Task 13 completed with spec compliance and code quality review approval after adding Dockerfile, Docker Compose services, README startup instructions, and `.dockerignore` build-context protection. Verification: `python -m pytest -q` passed with 52 tests and one third-party warning; `python -m ruff check app tests` passed; static compose parsing passed. Docker CLI was unavailable locally, so `docker compose config` could not be run.
- Task 14 completed with spec compliance and code quality review approval after adding end-to-end acceptance coverage, task detail export/card links, README verification commands, and manual smoke-check instructions. Verification: `python -m pytest tests/test_acceptance.py -q` passed with 1 test and one third-party warning; `python -m pytest -q` passed with 53 tests and one third-party warning; `python -m ruff check .` passed; Playwright manually verified search, task detail, Excel download, and due diligence card rendering. Docker CLI remained unavailable for compose runtime validation.
- Final implementation review failed on MVP readiness blockers: cross-platform searches only persisted the first selected platform, task detail did not show manager-ready candidate fields, and deployment had no access guardrails. Added remediation plan `docs/superpowers/plans/2026-06-09-final-review-remediation.md`.
- Task 15 completed after adding failing tests for selected-platform coverage, updating the manual fallback connector to return one deterministic candidate per selected platform, and adding `collect_raw_candidates()` for opportunistic YouTube live data plus fallback gap filling. Verification: targeted red tests failed before the fix, then `python -m pytest tests/test_search_runner.py -q` passed with 6 tests; `python -m ruff check app\connectors\manual.py app\services\search_runner.py tests\test_search_runner.py` passed.
- Task 16 completed after adding a failing task-detail route test for manager-ready fields and updating the task detail route/template to show creator name, platform, profile link, followers, average views, engagement rate, score, contact, reasons, risks, card, and follow-up controls. Verification: the route test failed before the fix, then `python -m pytest tests/test_acceptance.py tests/test_search_runner.py tests/test_web.py -q` passed with 14 tests and one third-party warning; `python -m ruff check app tests` passed.
