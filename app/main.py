from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import init_db
from app.security import basic_auth_challenge, is_authorized_basic_header
from app.web.routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def require_basic_auth(request: Request, call_next):
    if is_authorized_basic_header(
        request.headers.get("Authorization"),
        settings.access_username,
        settings.access_password,
    ):
        return await call_next(request)
    return basic_auth_challenge()


app.include_router(router)
