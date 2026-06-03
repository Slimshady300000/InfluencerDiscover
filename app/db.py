import importlib
from pathlib import Path
from typing import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def build_engine():
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///./data/"):
        Path("data").mkdir(exist_ok=True)
    is_sqlite = settings.database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    db_engine = create_engine(settings.database_url, connect_args=connect_args)

    if is_sqlite:
        @event.listens_for(db_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return db_engine


engine = build_engine()


def init_db() -> None:
    # Register table classes before creating metadata-backed tables.
    importlib.import_module("app.models")
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
