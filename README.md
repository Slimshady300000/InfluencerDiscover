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

## External Search APIs

The app works without API keys by using deterministic fallback candidates for local
review. For real public discovery, configure these values in `.env`:

```powershell
YOUTUBE_API_KEY=your-youtube-data-api-key
SEARCH_ENGINE_API_KEY=your-google-custom-search-json-api-key
SEARCH_ENGINE_ID=your-programmable-search-engine-id
```

`YOUTUBE_API_KEY` enables YouTube Data API search for YouTube candidates.
`SEARCH_ENGINE_API_KEY` plus `SEARCH_ENGINE_ID` enables cross-platform public
link discovery across YouTube, TikTok, and Instagram profile/result pages. TikTok
and Instagram are discovered through public search results in this MVP, not
through private scraping or unofficial platform APIs.

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
