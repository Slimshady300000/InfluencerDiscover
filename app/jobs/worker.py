from sqlmodel import Session

from app.db import engine
from app.services.search_runner import run_search_task


def run_search_task_job(task_id: int) -> None:
    with Session(engine) as session:
        run_search_task(session, task_id)
