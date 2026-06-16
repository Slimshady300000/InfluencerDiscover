from dataclasses import dataclass
import json
from statistics import mean

from sqlalchemy import delete
from sqlmodel import Session

from app.connectors.base import RawCandidate
from app.connectors.manual import ManualConnector
from app.connectors.search_engine import SearchEngineConnector
from app.connectors.tavily import TavilyConnector
from app.connectors.web_crawler import WebCrawlerConnector
from app.connectors.youtube import YouTubeConnector
from app.config import get_settings
from app.models import (
    ContactRecord,
    ContentSample,
    Creator,
    Platform,
    PlatformAccount,
    ScoreResult,
    SearchTask,
    TaskStatus,
)
from app.services.query_parser import SearchIntent, parse_search_input
from app.services.scoring import CandidateMetrics, score_batch


@dataclass(frozen=True)
class CandidateCollection:
    candidates: list[RawCandidate]
    connector_status: dict


def run_search_task(session: Session, task_id: int) -> None:
    task = session.get(SearchTask, task_id)
    if task is None:
        raise ValueError(f"Search task not found: {task_id}")

    task.status = TaskStatus.running
    session.add(task)
    session.commit()

    try:
        platforms = [Platform(value) for value in task.platforms.split(",") if value]
        intent = parse_search_input(task.input_text, platforms)
        collection = collect_candidates_with_status(intent, use_demo_data=task.use_demo_data)
        raw_candidates = collection.candidates
        session.exec(delete(ScoreResult).where(ScoreResult.task_id == task.id))

        task.connector_status = json.dumps(collection.connector_status, ensure_ascii=False)
        if not raw_candidates:
            task.status = TaskStatus.complete
            task.error_summary = collection.connector_status.get(
                "summary",
                "No real public results found.",
            )
            session.add(task)
            session.commit()
            return

        persisted = [_persist_candidate(session, candidate) for candidate in raw_candidates]
        metrics = [
            _metrics_for_candidate(candidate, creator_id, account_id)
            for candidate, creator_id, account_id in persisted
        ]

        for scored_candidate in score_batch(metrics):
            creator_id, account_id = [int(part) for part in scored_candidate.key.split(":")]
            session.add(
                ScoreResult(
                    task_id=task.id,
                    creator_id=creator_id,
                    platform_account_id=account_id,
                    normalized_views=scored_candidate.normalized_views,
                    normalized_engagement=scored_candidate.normalized_engagement,
                    normalized_followers=scored_candidate.normalized_followers,
                    topic_score=scored_candidate.topic_score,
                    data_performance_score=scored_candidate.data_performance_score,
                    contactability_score=scored_candidate.contactability_score,
                    final_score=scored_candidate.final_score,
                    reasons=" | ".join(scored_candidate.reasons),
                    risks=" | ".join(scored_candidate.risks),
                )
            )

        task.status = TaskStatus.complete
        task.error_summary = ""
        session.add(task)
        session.commit()
    except Exception as exc:
        session.rollback()
        failed_task = session.get(SearchTask, task_id)
        if failed_task is not None:
            failed_task.status = TaskStatus.failed
            failed_task.error_summary = str(exc)
            session.add(failed_task)
        session.commit()
        raise


def collect_raw_candidates(intent: SearchIntent) -> list[RawCandidate]:
    return collect_candidates_with_status(intent, use_demo_data=False).candidates


def collect_candidates_with_status(
    intent: SearchIntent,
    use_demo_data: bool = False,
) -> CandidateCollection:
    candidates: list[RawCandidate] = []
    live_platforms: set[Platform] = set()
    settings = get_settings()

    requested_platforms = intent.platforms or [Platform.youtube]

    has_tavily = bool(settings.tavily_api_key)
    connector_status = _base_connector_status(
        requested_platforms,
        mode="real_tavily_search" if has_tavily else "real_crawler",
    )

    if has_tavily:
        try:
            tavily = TavilyConnector(api_key=settings.tavily_api_key)
            tavily_candidates = tavily.search(_intent_for_platforms(intent, requested_platforms))
        except Exception as exc:
            tavily_candidates = []
            connector_status["errors"].append(f"tavily api failed: {exc}")
        else:
            connector_status["platforms"].update(tavily.last_status)

        candidates.extend(tavily_candidates)
        live_platforms.update(candidate.platform for candidate in tavily_candidates)
    else:
        try:
            crawler = WebCrawlerConnector()
            crawler_candidates = crawler.search(_intent_for_platforms(intent, requested_platforms))
        except Exception as exc:
            crawler_candidates = []
            connector_status["errors"].append(f"crawler failed: {exc}")
        else:
            connector_status["platforms"].update(crawler.last_status)

        candidates.extend(crawler_candidates)
        live_platforms.update(candidate.platform for candidate in crawler_candidates)

    api_platforms = [platform for platform in requested_platforms if platform not in live_platforms]
    if Platform.youtube in api_platforms and settings.youtube_api_key:
        try:
            with YouTubeConnector(api_key=settings.youtube_api_key) as connector:
                youtube_candidates = connector.search(_intent_for_platforms(intent, [Platform.youtube]))
        except Exception as exc:
            youtube_candidates = []
            connector_status["errors"].append(f"youtube api failed: {exc}")
        if youtube_candidates:
            candidates.extend(youtube_candidates)
            live_platforms.add(Platform.youtube)

    search_platforms = [platform for platform in requested_platforms if platform not in live_platforms]
    if search_platforms and settings.search_engine_api_key and settings.search_engine_id:
        search_intent = _intent_for_platforms(intent, search_platforms)
        try:
            search_candidates = SearchEngineConnector(
                api_key=settings.search_engine_api_key,
                search_engine_id=settings.search_engine_id,
            ).search(search_intent)
        except Exception as exc:
            search_candidates = []
            connector_status["errors"].append(f"search engine api failed: {exc}")
        if search_candidates:
            candidates.extend(search_candidates)
            live_platforms.update(candidate.platform for candidate in search_candidates)

    fallback_platforms = [platform for platform in requested_platforms if platform not in live_platforms]
    if fallback_platforms and use_demo_data:
        fallback_intent = _intent_for_platforms(intent, fallback_platforms)
        candidates.extend(ManualConnector().search(fallback_intent))

    deduped_candidates = _dedupe_and_limit(candidates, requested_platforms)
    real_count = sum(
        1 for candidate in deduped_candidates if candidate.data_source != "demo_fallback"
    )
    demo_count = sum(
        1 for candidate in deduped_candidates if candidate.data_source == "demo_fallback"
    )
    connector_status["real_result_count"] = real_count
    connector_status["demo_used"] = demo_count > 0
    connector_status["demo_result_count"] = demo_count
    connector_status["summary"] = _status_summary(real_count, demo_count, use_demo_data)
    return CandidateCollection(candidates=deduped_candidates, connector_status=connector_status)


def _intent_for_platforms(intent: SearchIntent, platforms: list[Platform]) -> SearchIntent:
    return SearchIntent(
        input_text=intent.input_text,
        input_type=intent.input_type,
        platforms=platforms,
        core_terms=intent.core_terms,
        expanded_terms=intent.expanded_terms,
        seed_urls=intent.seed_urls,
    )


def _persist_candidate(session: Session, candidate: RawCandidate) -> tuple[RawCandidate, int, int]:
    creator = Creator(display_name=candidate.display_name, primary_topics=candidate.bio)
    account = PlatformAccount(
        creator=creator,
        platform=candidate.platform,
        handle=candidate.handle,
        profile_url=candidate.profile_url,
        follower_count=candidate.follower_count,
        bio=candidate.bio,
        avatar_url=candidate.avatar_url,
        data_source=candidate.data_source,
    )
    session.add(account)
    session.flush()

    for content in candidate.contents:
        session.add(
            ContentSample(
                account_id=account.id,
                content_url=content.content_url,
                title=content.title,
                description=content.description,
                hashtags=",".join(content.hashtags),
                view_count=content.view_count,
                like_count=content.like_count,
                comment_count=content.comment_count,
                share_count=content.share_count,
            )
        )

    for contact in candidate.contacts:
        session.add(
            ContactRecord(
                creator_id=creator.id,
                contact_type=contact.contact_type,
                value=contact.value,
                source_url=contact.source_url,
                is_public=contact.is_public,
            )
        )

    return candidate, creator.id, account.id


def _base_connector_status(platforms: list[Platform], mode: str = "real_crawler") -> dict:
    return {
        "mode": mode,
        "searched_platforms": [platform.value for platform in platforms],
        "real_result_count": 0,
        "demo_used": False,
        "demo_result_count": 0,
        "summary": "",
        "platforms": {},
        "errors": [],
    }


def _dedupe_and_limit(candidates: list[RawCandidate], platforms: list[Platform]) -> list[RawCandidate]:
    seen_urls: set[str] = set()
    platform_counts = {platform: 0 for platform in platforms}
    deduped: list[RawCandidate] = []

    for candidate in candidates:
        if candidate.platform not in platform_counts:
            continue
        normalized_url = candidate.profile_url.strip().lower().rstrip("/")
        if not normalized_url or normalized_url in seen_urls:
            continue
        if platform_counts[candidate.platform] >= 20:
            continue
        seen_urls.add(normalized_url)
        platform_counts[candidate.platform] += 1
        deduped.append(candidate)

    return deduped


def _status_summary(real_count: int, demo_count: int, use_demo_data: bool) -> str:
    if real_count == 0 and demo_count == 0:
        return "No real public results found."
    if real_count == 0 and demo_count > 0 and use_demo_data:
        return "No real public results found. Demo fallback enabled."
    if real_count > 0 and demo_count > 0:
        return "Real public results found. Demo fallback filled missing platforms."
    return "Real public results found."


def _metrics_for_candidate(
    candidate: RawCandidate,
    creator_id: int,
    account_id: int,
) -> CandidateMetrics:
    views = [content.view_count for content in candidate.contents]
    likes = sum(content.like_count for content in candidate.contents)
    comments = sum(content.comment_count for content in candidate.contents)
    average_views = int(mean(views)) if views else 0
    engagement_rate = (likes + comments) / max(sum(views), 1)
    has_public_contact = any(contact.is_public for contact in candidate.contacts)
    has_dm_entry = candidate.platform in {Platform.tiktok, Platform.instagram}
    topic_text = f"{candidate.bio} {candidate.display_name}".lower()
    topic_score = 0.8 if "skincare" in topic_text else 0.4

    return CandidateMetrics(
        key=f"{creator_id}:{account_id}",
        platform=candidate.platform.value,
        follower_count=candidate.follower_count,
        recent_view_count=average_views,
        engagement_rate=engagement_rate,
        topic_score=topic_score,
        has_public_contact=has_public_contact,
        has_dm_entry=has_dm_entry,
    )
