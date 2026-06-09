# Search UI And API Upgrade Design

## Goal
Make the current MVP easier to use in a 10-person media team by improving the UI, returning enough candidates for review, and wiring the existing search API settings into a real connector path.

## Scope
- Improve the existing server-rendered FastAPI/Jinja pages, not introduce a SPA framework.
- Increase deterministic fallback results so internal users can evaluate ranking, export, and review flows without external keys.
- Add a Google Programmable Search / Custom Search compatible connector using `SEARCH_ENGINE_API_KEY` and `SEARCH_ENGINE_ID`.
- Keep YouTube Data API support as-is: it is used only when `YOUTUBE_API_KEY` is configured.
- Do not add unofficial TikTok or Instagram scraping in this pass.

## UX Design
The app remains an operations tool. The search page gets a stronger header, a clear search input, chip-like platform selectors, a primary search button, and recent tasks with status badges. The task detail page becomes a denser review workspace with a sticky-style action row, clearer export/review buttons, badges for platforms, and readable metric columns.

## Candidate Strategy
When no external keys are configured, fallback data returns at least 8 candidates per selected platform. This gives a three-platform search 24 candidates, enough to test sorting and review. When search engine credentials are configured, the search connector returns candidates from public result links and the fallback fills remaining gaps.

## API Strategy
The new connector calls `https://www.googleapis.com/customsearch/v1` with `key`, `cx`, and a query that combines the user search terms with platform site filters. Results are converted to `RawCandidate` records using title, snippet, link, detected platform, inferred handle, and conservative default metrics. If credentials are missing or the API returns no usable candidates, the existing fallback path keeps the product usable.

## Verification
- Unit tests cover fallback candidate count, search engine request parameters, payload parsing, and runner integration.
- Web tests cover the upgraded template structure and visible controls.
- Existing acceptance, export, security, and scoring tests must continue to pass.
- Browser smoke verifies the redesigned UI, three-platform search result volume, export, and card flow.
