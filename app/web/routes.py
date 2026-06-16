import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.jobs.queue import get_queue
from app.jobs.worker import run_search_task_job
from app.models import (
    ContentSample,
    Creator,
    FollowUp,
    PlatformAccount,
    ScoreResult,
    SearchTask,
    TaskStatus,
    utc_now,
)
from app.services.due_diligence import build_due_diligence_card
from app.services.exporter import build_candidate_workbook
from app.services.search_runner import run_search_task

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def search_page(request: Request, session: Session = Depends(get_session)):
    tasks = session.exec(select(SearchTask).order_by(SearchTask.created_at.desc())).all()
    task_rows = [
        {
            "task": task,
            "status_label": _task_status_label(task.status),
            "platforms_label": _platforms_label(task.platforms),
        }
        for task in tasks
    ]
    return templates.TemplateResponse(request, "search.html", {"task_rows": task_rows})


@router.post("/search")
def create_search_task(
    input_text: str = Form(min_length=1),
    platforms: list[str] = Form(default=["youtube", "tiktok", "instagram"]),
    use_demo_data: list[str] = Form(default=[]),
    run_inline: list[str] = Form(default=["yes"]),
    session: Session = Depends(get_session),
):
    task = SearchTask(
        input_text=input_text,
        input_type="keyword",
        platforms=",".join(platforms),
        status=TaskStatus.queued,
        use_demo_data="yes" in use_demo_data,
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
        raise HTTPException(status_code=404, detail="搜索任务不存在")
    connector_status = _parse_connector_status(task.connector_status)
    return templates.TemplateResponse(
        request,
        "task_detail.html",
        {
            "task": task,
            "task_status_label": _task_status_label(task.status),
            "task_error_summary": _localize_text(task.error_summary),
            "result_rows": _build_task_result_rows(task),
            "connector_status": connector_status,
        },
    )


@router.get("/tasks/{task_id}/export.xlsx")
def export_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(SearchTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="搜索任务不存在")

    rows = []
    for result in task.results:
        creator = session.get(Creator, result.creator_id)
        account = session.get(PlatformAccount, result.platform_account_id)
        contact = creator.contacts[0].value if creator and creator.contacts else ""
        rows.append(
            {
                "creator": creator.display_name if creator else "",
                "platform": account.platform.value if account else "",
                "followers": _follower_count_export_value(account),
                "recent_views": _average_recent_views_export_value(account),
                "engagement_rate": _engagement_rate_export_value(account),
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
        raise HTTPException(status_code=404, detail="评分结果不存在")

    creator = session.get(Creator, result.creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail="达人不存在")

    account = session.get(PlatformAccount, result.platform_account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")

    titles = [sample.title for sample in account.content_samples]
    contact = creator.contacts[0].value if creator.contacts else ""
    card = build_due_diligence_card(
        creator_name=creator.display_name,
        platform=account.platform.value,
        follower_count=account.follower_count,
        follower_label=_follower_count_label(account),
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
        raise HTTPException(status_code=404, detail="达人不存在")
    if session.get(SearchTask, task_id) is None:
        raise HTTPException(status_code=404, detail="搜索任务不存在")

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
                "average_views_label": _average_recent_views_label(account),
                "engagement_rate_label": _engagement_rate_label(account),
                "follower_count_label": _follower_count_label(account),
                "follow_up": follow_up,
                "source_label": _source_label(account.data_source if account else ""),
                "source_class": account.data_source if account else "unknown",
                "reason_summary": _short_reason_summary(result.reasons),
                "reason_details": _localize_pipe_text(result.reasons),
                "risk_details": _localize_pipe_text(result.risks),
                "representative_content": _representative_content(account),
            }
        )
    return rows


def _parse_connector_status(raw_status: str) -> dict:
    if not raw_status:
        return {
            "mode": "real_crawler",
            "searched_platforms": [],
            "real_result_count": 0,
            "demo_used": False,
            "demo_result_count": 0,
            "summary": "",
            "platforms": {},
            "errors": [],
        }
    try:
        parsed = json.loads(raw_status)
    except json.JSONDecodeError:
        return {
            "mode": "real_crawler",
            "searched_platforms": [],
            "real_result_count": 0,
            "demo_used": False,
            "demo_result_count": 0,
            "summary": _localize_text(raw_status),
            "platforms": {},
            "errors": [_localize_text(raw_status)],
        }
    return _localize_connector_status(parsed) if isinstance(parsed, dict) else {}


def _source_label(data_source: str) -> str:
    if data_source == "demo_fallback":
        return "演示数据"
    return "真实公开结果"


def _task_status_label(status: TaskStatus | str) -> str:
    return {
        TaskStatus.queued: "排队中",
        TaskStatus.running: "运行中",
        TaskStatus.complete: "已完成",
        TaskStatus.failed: "失败",
        "queued": "排队中",
        "running": "运行中",
        "complete": "已完成",
        "failed": "失败",
    }.get(status, str(status))


def _platforms_label(platforms: str) -> str:
    labels = {
        "youtube": "YouTube",
        "tiktok": "TikTok",
        "instagram": "Instagram",
        "web": "网页",
    }
    return " / ".join(labels.get(platform, platform) for platform in platforms.split(",") if platform)


def _short_reason_summary(reasons: str) -> str:
    if not reasons:
        return "评分基于当前可用的公开主页和内容信号。"
    return _localize_text(reasons.split(" | ", 1)[0])


def _localize_connector_status(status: dict) -> dict:
    localized = dict(status)
    localized["summary"] = _localize_text(str(localized.get("summary", "")))
    localized["errors"] = [
        _localize_text(str(error)) for error in localized.get("errors", [])
    ]

    platform_statuses = {}
    for platform, platform_status in localized.get("platforms", {}).items():
        if not isinstance(platform_status, dict):
            platform_statuses[platform] = platform_status
            continue
        updated_status = dict(platform_status)
        updated_status["errors"] = [
            _localize_text(str(error)) for error in updated_status.get("errors", [])
        ]
        platform_statuses[platform] = updated_status
    localized["platforms"] = platform_statuses
    return localized


def _localize_pipe_text(value: str) -> str:
    if not value:
        return ""
    return " | ".join(_localize_text(part.strip()) for part in value.split(" | ") if part.strip())


def _localize_text(value: str) -> str:
    translations = {
        "No real public results found.": "未找到真实公开结果。",
        "No real public results found. Demo fallback enabled.": "未找到真实公开结果，已启用演示数据。",
        "Real public results found. Demo fallback filled missing platforms.": "已找到真实公开结果，演示数据补齐了缺失平台。",
        "Real public results found.": "已找到真实公开结果。",
        "search source returned no usable links": "搜索源没有返回可用链接。",
        "tavily returned no usable profile links": "Tavily 没有返回可用的主页链接。",
        "Ranking score is based on available public profile and content signals.": "评分基于当前可用的公开主页和内容信号。",
        "Ranked mainly by recent views, engagement rate, and follower count.": "主要根据近期播放、互动率和粉丝数排序。",
        "Compared within the same platform batch.": "已在同平台候选中比较。",
        "Topic match is weak and needs manager review.": "话题匹配度偏弱，需要人工复核。",
        "No public business contact found.": "未找到公开商务联系方式。",
        "Strong topic fit": "话题匹配度高",
        "Public contact found": "找到公开联系方式",
        "Recent content present": "已有近期内容样本",
        "connector unavailable": "连接器不可用",
    }
    if value in translations:
        return translations[value]
    if value.startswith("profile fetch failed for "):
        return f"主页抓取失败：{value.removeprefix('profile fetch failed for ')}"
    if value.startswith("tavily request failed: "):
        return f"Tavily 请求失败：{value.removeprefix('tavily request failed: ')}"
    if value.startswith("crawler failed: "):
        return f"公开爬虫失败：{value.removeprefix('crawler failed: ')}"
    if value.startswith("youtube api failed: "):
        return f"YouTube API 失败：{value.removeprefix('youtube api failed: ')}"
    if value.startswith("search engine api failed: "):
        return f"搜索 API 失败：{value.removeprefix('search engine api failed: ')}"
    return value


def _representative_content(account: PlatformAccount | None) -> ContentSample | None:
    if account is None or not account.content_samples:
        return None
    return account.content_samples[0]


def _first_contact(creator: Creator | None) -> str:
    if creator is None or not creator.contacts:
        return ""
    return creator.contacts[0].value


def _follower_count_label(account: PlatformAccount | None) -> str:
    value = _follower_count_export_value(account)
    return str(value)


def _follower_count_export_value(account: PlatformAccount | None) -> int | str:
    if account is None:
        return "未获取"
    if account.follower_count <= 0 and account.data_source != "demo_fallback":
        return "未获取"
    return account.follower_count


def _average_recent_views(account: PlatformAccount | None) -> int:
    if account is None or not account.content_samples:
        return 0
    views = [sample.view_count for sample in account.content_samples]
    return sum(views) // len(views)


def _average_recent_views_label(account: PlatformAccount | None) -> str:
    value = _average_recent_views_export_value(account)
    return str(value)


def _average_recent_views_export_value(account: PlatformAccount | None) -> int | str:
    average_views = _average_recent_views(account)
    if average_views <= 0 and (account is None or account.data_source != "demo_fallback"):
        return "未获取"
    return average_views


def _engagement_rate(account: PlatformAccount | None) -> float:
    if account is None or not account.content_samples:
        return 0.0
    views = sum(sample.view_count for sample in account.content_samples)
    interactions = sum(
        sample.like_count + sample.comment_count + sample.share_count
        for sample in account.content_samples
    )
    return interactions / max(views, 1)


def _engagement_rate_label(account: PlatformAccount | None) -> str:
    engagement_rate = _engagement_rate(account)
    if engagement_rate <= 0 and (account is None or account.data_source != "demo_fallback"):
        return "未获取"
    return f"{engagement_rate:.2%}"


def _engagement_rate_export_value(account: PlatformAccount | None) -> float | str:
    engagement_rate = _engagement_rate(account)
    if engagement_rate <= 0 and (account is None or account.data_source != "demo_fallback"):
        return "未获取"
    return engagement_rate
