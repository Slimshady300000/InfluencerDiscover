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

Open `http://localhost:8000`.

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
