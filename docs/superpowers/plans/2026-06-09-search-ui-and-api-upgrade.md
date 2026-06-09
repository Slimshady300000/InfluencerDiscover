# Search UI And API Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the MVP interface, candidate volume, and real search API path without changing the core FastAPI/Jinja architecture.

**Architecture:** Keep server-rendered templates and add richer CSS classes to the existing pages. Expand deterministic fallback data inside `ManualConnector`, and add a `SearchEngineConnector` that converts Custom Search JSON results into `RawCandidate` rows. `collect_raw_candidates()` will prefer configured live connectors and fill gaps with fallback data.

**Tech Stack:** FastAPI, Jinja2, SQLModel, httpx, pytest, Ruff, Playwright CLI.

---

### Task 20: UI Polish

**Files:**
- Modify: `app/templates/layout.html`
- Modify: `app/templates/search.html`
- Modify: `app/templates/task_detail.html`
- Modify: `app/static/app.css`
- Test: `tests/test_web.py`

- [ ] Add a failing test that renders `/` and expects `hero-panel`, `platform-option`, `primary-button`, and status badge markup.
- [ ] Update templates with semantic classes for search, task status, buttons, platform badges, metrics, and review actions.
- [ ] Replace the minimal CSS with a polished operations-tool visual system.
- [ ] Run `python -m pytest tests/test_web.py -q`.

### Task 21: Fallback Candidate Volume

**Files:**
- Modify: `app/connectors/manual.py`
- Test: `tests/test_search_runner.py`
- Test: `tests/test_acceptance.py`

- [ ] Add a failing test that a three-platform manual search returns at least 24 candidates and at least 8 candidates per platform.
- [ ] Expand fallback fixtures with generated variants per platform.
- [ ] Update acceptance coverage to assert a three-platform search returns enough rows.
- [ ] Run `python -m pytest tests/test_search_runner.py tests/test_acceptance.py -q`.

### Task 22: Search Engine API Connector

**Files:**
- Modify: `app/connectors/search_engine.py`
- Modify: `app/services/search_runner.py`
- Test: `tests/test_search_engine_connector.py`
- Test: `tests/test_search_runner.py`
- Modify: `README.md`

- [ ] Add failing tests for Custom Search params, empty credentials, result parsing, malformed URL rejection, and search runner usage when credentials are configured.
- [ ] Implement `SearchEngineConnector` with injectable httpx client and safe parsing.
- [ ] Wire `collect_raw_candidates()` to use the connector when `SEARCH_ENGINE_API_KEY` and `SEARCH_ENGINE_ID` are configured.
- [ ] Document required API keys and current platform limitations.
- [ ] Run `python -m pytest tests/test_search_engine_connector.py tests/test_search_runner.py -q`.

### Task 23: Verification And Browser QA

**Files:**
- Modify: `tasks/todo.md`

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m ruff check .`.
- [ ] Restart local uvicorn.
- [ ] Use Playwright CLI to verify the redesigned UI, three-platform candidate volume, Excel export, and card route.
- [ ] Record results in `tasks/todo.md`.
