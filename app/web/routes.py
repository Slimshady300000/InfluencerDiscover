from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.jobs.queue import get_queue
from app.jobs.worker import run_search_task_job
from app.models import Creator, FollowUp, PlatformAccount, ScoreResult, SearchTask, TaskStatus, utc_now
from app.services.due_diligence import build_due_diligence_card
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
    run_inline: list[str] = Form(default=["yes"]),
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
        if "yes" in run_inline:
            run_search_task(session, task.id)
        else:
            get_queue().enqueue(run_search_task_job, task.id)
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
    return templates.TemplateResponse(
        request,
        "task_detail.html",
        {"task": task, "result_rows": _build_task_result_rows(task)},
    )


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
        rows.append(
            {
                "creator": creator.display_name if creator else "",
                "platform": account.platform.value if account else "",
                "followers": account.follower_count if account else 0,
                "recent_views": _average_recent_views(account),
                "engagement_rate": _engagement_rate(account),
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


@router.get("/results/{result_id}/card")
def result_card(result_id: int, request: Request, session: Session = Depends(get_session)):
    result = session.get(ScoreResult, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Score result not found")

    creator = session.get(Creator, result.creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail="Creator not found")

    account = session.get(PlatformAccount, result.platform_account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Platform account not found")

    titles = [sample.title for sample in account.content_samples]
    contact = creator.contacts[0].value if creator.contacts else ""
    card = build_due_diligence_card(
        creator_name=creator.display_name,
        platform=account.platform.value,
        follower_count=account.follower_count,
        score=result.final_score,
        content_titles=titles,
        contact=contact,
        risks=[result.risks] if result.risks else [],
    )
    return templates.TemplateResponse(request, "card.html", {"card": card})


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


def _build_task_result_rows(task: SearchTask) -> list[dict]:
    rows = []
    for result in sorted(task.results, key=lambda item: item.final_score, reverse=True):
        creator = result.creator
        account = result.platform_account
        contact = _first_contact(creator)
        follow_up = creator.follow_ups[0] if creator and creator.follow_ups else None
        rows.append(
            {
                "result": result,
                "creator": creator,
                "account": account,
                "contact": contact,
                "average_views": _average_recent_views(account),
                "engagement_rate_label": f"{_engagement_rate(account):.2%}",
                "follow_up": follow_up,
            }
        )
    return rows


def _first_contact(creator: Creator | None) -> str:
    if creator is None or not creator.contacts:
        return ""
    return creator.contacts[0].value


def _average_recent_views(account: PlatformAccount | None) -> int:
    if account is None or not account.content_samples:
        return 0
    views = [sample.view_count for sample in account.content_samples]
    return sum(views) // len(views)


def _engagement_rate(account: PlatformAccount | None) -> float:
    if account is None or not account.content_samples:
        return 0.0
    views = sum(sample.view_count for sample in account.content_samples)
    interactions = sum(
        sample.like_count + sample.comment_count + sample.share_count
        for sample in account.content_samples
    )
    return interactions / max(views, 1)
