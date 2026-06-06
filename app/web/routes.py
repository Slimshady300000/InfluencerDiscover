from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models import SearchTask, TaskStatus
from app.services.search_runner import run_search_task

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def search_page(request: Request, session: Session = Depends(get_session)):
    tasks = session.exec(select(SearchTask).order_by(SearchTask.created_at.desc())).all()
    return templates.TemplateResponse(request, "search.html", {"tasks": tasks})


@router.post("/search")
def create_search_task(
    input_text: str = Form(min_length=1),
    platforms: list[str] = Form(default=["youtube"]),
    session: Session = Depends(get_session),
):
    task = SearchTask(
        input_text=input_text,
        input_type="keyword",
        platforms=",".join(platforms),
        status=TaskStatus.queued,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    run_search_task(session, task.id)
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=303)


@router.get("/tasks/{task_id}")
def task_detail(task_id: int, request: Request, session: Session = Depends(get_session)):
    task = session.get(SearchTask, task_id)
    return templates.TemplateResponse(request, "task_detail.html", {"task": task})
