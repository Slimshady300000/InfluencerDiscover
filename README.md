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
