from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return "<h1>Influencer Discovery</h1><p>Search creator candidates.</p>"
