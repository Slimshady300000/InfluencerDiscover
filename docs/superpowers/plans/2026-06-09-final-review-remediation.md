# Final Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the final review blockers so the internal influencer discovery MVP can be handed off honestly.

**Architecture:** Keep the MVP local-first and deterministic by improving the existing manual connector into a multi-platform fallback while allowing the YouTube connector to contribute when configured. Enrich the existing task-detail route with view rows instead of changing the persistence model. Add deployment safety through host-only Docker publishing plus optional HTTP Basic Auth.

**Tech Stack:** FastAPI, SQLModel, Jinja2, openpyxl, pytest, Ruff, Docker Compose.

---

### Task 15: Multi-Platform Candidate Discovery

**Files:**
- Modify: `app/connectors/manual.py`
- Modify: `app/services/search_runner.py`
- Test: `tests/test_search_runner.py`
- Test: `tests/test_acceptance.py`

- [ ] Write a failing test that creates a search task with `youtube,tiktok,instagram` and expects one persisted account and one score result per selected platform.
- [ ] Verify the test fails because only the first selected platform is persisted.
- [ ] Update `ManualConnector.search()` to return deterministic candidate fixtures for every selected platform.
- [ ] Add a small `collect_raw_candidates()` path in `search_runner.py` that can use the YouTube connector when `YOUTUBE_API_KEY` is configured and always fills missing requested platforms with manual fallback candidates.
- [ ] Verify `python -m pytest tests/test_search_runner.py -q` passes.

### Task 16: Manager-Usable Candidate Table

**Files:**
- Modify: `app/web/routes.py`
- Modify: `app/templates/task_detail.html`
- Test: `tests/test_web.py`
- Test: `tests/test_acceptance.py`

- [ ] Write a failing route test that expects task detail HTML to include creator name, platform, profile URL, follower count, average recent views, engagement rate, and contact value.
- [ ] Verify the test fails with the current ID-only candidate table.
- [ ] Build candidate view rows in `task_detail()` from `ScoreResult`, `Creator`, `PlatformAccount`, content samples, contacts, and follow-up state.
- [ ] Update the table headers and cells to show the required manager review fields while preserving export, card, and follow-up actions.
- [ ] Verify `python -m pytest tests/test_web.py tests/test_acceptance.py -q` passes.

### Task 17: Internal Access Guardrails

**Files:**
- Create: `app/security.py`
- Modify: `app/config.py`
- Modify: `app/main.py`
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `README.md`
- Test: `tests/test_security.py`

- [ ] Write failing tests for HTTP Basic Auth: no credentials means local dev remains open; configured credentials return 401 without auth and 200 with valid auth.
- [ ] Verify the tests fail because no access middleware exists.
- [ ] Add optional `ACCESS_USERNAME` and `ACCESS_PASSWORD` settings.
- [ ] Add FastAPI middleware that enforces Basic Auth only when both credentials are configured.
- [ ] Bind the web service to `127.0.0.1:8000:8000` in Docker Compose and stop publishing Redis to the host.
- [ ] Document local-only Docker exposure and the optional Basic Auth environment variables.
- [ ] Verify `python -m pytest tests/test_security.py -q` passes.

### Task 18: Excel Formula Injection Guard

**Files:**
- Modify: `app/services/exporter.py`
- Test: `tests/test_exporter.py`

- [ ] Write a failing exporter test where creator/contact text starts with `=`, `+`, `-`, and `@`.
- [ ] Verify the generated workbook currently writes formula-like values directly.
- [ ] Prefix formula-like string values with an apostrophe before appending cells.
- [ ] Verify `python -m pytest tests/test_exporter.py -q` passes.

### Task 19: Final Verification And Review

**Files:**
- Modify: `tasks/todo.md`

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m ruff check .`.
- [ ] Run a browser smoke check against `http://127.0.0.1:8000` for all three platforms, Excel export, and due diligence card rendering.
- [ ] Ask for final read-only review again.
- [ ] Mark remediation tasks complete in `tasks/todo.md` only after the review passes.
