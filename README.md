# Influencer Discovery

Internal MVP for finding, scoring, reviewing, and exporting overseas influencer candidates.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
uvicorn app.main:app --reload
```

## Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8000`. The compose file binds the web service to `127.0.0.1`
and does not publish Redis to the host. For shared internal use, run it behind
your company VPN or reverse proxy and set `ACCESS_USERNAME` plus `ACCESS_PASSWORD`
in `.env` to enable browser HTTP Basic Auth.

## Public Search And Optional APIs

For reliable real discovery, configure Tavily in `.env`:

```powershell
TAVILY_API_KEY=your-tavily-api-key
```

When `TAVILY_API_KEY` is set, the app uses Tavily Search API as the primary
cross-platform discovery source. It searches each selected platform with domain
filters:

- `youtube.com`
- `tiktok.com`
- `instagram.com`

The app parses result titles, snippets, URLs, platform handles, public profile
metadata, and public email addresses when they appear on fetched pages. It does
not log in, bypass CAPTCHA, simulate user accounts, or collect private data.

If Tavily is not configured, the app falls back to a lightweight public web
crawler that queries public search result pages with platform filters such as:

- `site:youtube.com skincare creator contact`
- `site:tiktok.com skincare creator contact`
- `site:instagram.com skincare creator contact`

Demo data is separated from real public results. It is only added when the search
form's `Use demo data if no real results` switch is enabled. If public search
returns no usable links and demo data is off, the task page shows an empty state
plus connector status instead of silently inserting fake creators.

For richer real discovery, configure these optional values in `.env`:

```powershell
YOUTUBE_API_KEY=your-youtube-data-api-key
```

`YOUTUBE_API_KEY` enables YouTube Data API search for YouTube candidates when
the primary public search path did not find YouTube results. TikTok and
Instagram are discovered through public search results in this MVP, not through
private scraping or unofficial platform APIs.

Public pages may rate-limit, block, or omit useful profile data. Follower counts,
view counts, and engagement metrics are not guaranteed through public crawling.
Use official APIs, paid data providers, or manual review for precise audience and
performance metrics.

## Verification

```powershell
python -m pytest -q
python -m ruff check app tests
```

Manual smoke check:

1. Start the app with `uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000`.
3. Search for a topic such as `skincare`.
4. Open the completed task detail page and confirm candidate rows are ranked.
5. Download the Excel export from `Export Excel`.
6. Open a candidate `Review card` page and confirm the recommendation, content summary, data highlights, risks, and suggested contact section render.
