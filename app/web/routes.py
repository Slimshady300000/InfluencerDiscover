from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models import Creator, FollowUp, PlatformAccount, SearchTask, TaskStatus, utc_now
from app.services.exporter import build_candidate_workbook
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
    try:
        run_search_task(session, task.id)
    except Exception as exc:
        session.rollback()
        failed_task = session.get(SearchTask, task.id)
        if failed_task is not None and failed_task.status != TaskStatus.failed:
            failed_task.status = TaskStatus.failed
            failed_task.error_summary = str(exc)
            session.add(failed_task)
            session.commit()
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=303)


@router.get("/tasks/{task_id}")
def task_detail(task_id: int, request: Request, session: Session = Depends(get_session)):
    task = session.get(SearchTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Search task not found")
    return templates.TemplateResponse(request, "task_detail.html", {"task": task})


@router.get("/tasks/{task_id}/export.xlsx")
def export_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(SearchTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Search task not found")

    rows = []
    for result in task.results:
        creator = session.get(Creator, result.creator_id)
        account = session.get(PlatformAccount, result.platform_account_id)
        contact = creator.contacts[0].value if creator and creator.contacts else ""
        view_counts = [sample.view_count for sample in account.content_samples] if account else []
        recent_views = sum(view_counts) // len(view_counts) if view_counts else 0
        rows.append(
            {
                "creator": creator.display_name if creator else "",
                "platform": account.platform.value if account else "",
                "followers": account.follower_count if account else 0,
                "recent_views": recent_views,
                "engagement_rate": result.normalized_engagement,
                "score": result.final_score,
                "contact": contact,
            }
        )
    payload = build_candidate_workbook(rows)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="task-{task_id}-candidates.xlsx"'},
    )


@router.post("/creators/{creator_id}/follow-up")
def update_follow_up(
    creator_id: int,
    task_id: int = Form(),
    owner: str = Form(default=""),
    status: str = Form(default=""),
    tags: str = Form(default=""),
    notes: str = Form(default=""),
    session: Session = Depends(get_session),
):
    creator = session.get(Creator, creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail="Creator not found")
    if session.get(SearchTask, task_id) is None:
        raise HTTPException(status_code=404, detail="Search task not found")

    follow_up = session.exec(select(FollowUp).where(FollowUp.creator_id == creator_id)).first()
    if follow_up is None:
        follow_up = FollowUp(creator_id=creator_id)

    follow_up.owner = owner
    follow_up.status = status
    follow_up.tags = tags
    follow_up.notes = notes
    follow_up.updated_at = utc_now()
    session.add(follow_up)
    session.commit()

    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)
