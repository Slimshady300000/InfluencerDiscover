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
    _ensure_sqlite_columns(engine)


def _ensure_sqlite_columns(db_engine) -> None:
    if db_engine.dialect.name != "sqlite":
        return

    with db_engine.begin() as connection:
        account_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(platformaccount)")
        }
        if "data_source" not in account_columns:
            connection.exec_driver_sql(
                "ALTER TABLE platformaccount "
                "ADD COLUMN data_source VARCHAR NOT NULL DEFAULT 'real_public'"
            )

        task_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(searchtask)")}
        if "use_demo_data" not in task_columns:
            connection.exec_driver_sql(
                "ALTER TABLE searchtask ADD COLUMN use_demo_data BOOLEAN NOT NULL DEFAULT 0"
            )
        if "connector_status" not in task_columns:
            connection.exec_driver_sql(
                "ALTER TABLE searchtask ADD COLUMN connector_status VARCHAR NOT NULL DEFAULT ''"
            )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
