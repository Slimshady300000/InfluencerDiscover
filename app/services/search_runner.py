from statistics import mean

from sqlalchemy import delete
from sqlmodel import Session

from app.connectors.base import RawCandidate
from app.connectors.manual import ManualConnector
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
from app.services.query_parser import parse_search_input
from app.services.scoring import CandidateMetrics, score_batch


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
        raw_candidates = ManualConnector().search(intent)
        session.exec(delete(ScoreResult).where(ScoreResult.task_id == task.id))
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
