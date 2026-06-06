from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateMetrics:
    key: str
    platform: str
    follower_count: int
    recent_view_count: int
    engagement_rate: float
    topic_score: float
    has_public_contact: bool
    has_dm_entry: bool


@dataclass(frozen=True)
class ScoredCandidate:
    key: str
    platform: str
    normalized_views: float
    normalized_engagement: float
    normalized_followers: float
    topic_score: float
    data_performance_score: float
    contactability_score: float
    final_score: float
    reasons: list[str]
    risks: list[str]


def score_batch(
    candidates: list[CandidateMetrics],
    minimum_topic_score: float = 0.2,
) -> list[ScoredCandidate]:
    eligible = [candidate for candidate in candidates if candidate.topic_score >= minimum_topic_score]
    if not eligible:
        return []
    scored: list[ScoredCandidate] = []
    for platform in sorted({candidate.platform for candidate in eligible}):
        platform_candidates = [candidate for candidate in eligible if candidate.platform == platform]
        max_views = max(candidate.recent_view_count for candidate in platform_candidates) or 1
        max_engagement = max(candidate.engagement_rate for candidate in platform_candidates) or 1
        max_followers = max(candidate.follower_count for candidate in platform_candidates) or 1
        for candidate in platform_candidates:
            normalized_views = candidate.recent_view_count / max_views
            normalized_engagement = candidate.engagement_rate / max_engagement
            normalized_followers = candidate.follower_count / max_followers
            data_score = (
                normalized_views * 0.35
                + normalized_engagement * 0.25
                + normalized_followers * 0.15
            ) / 0.75
            contact_score = 1.0 if candidate.has_public_contact else 0.5 if candidate.has_dm_entry else 0.0
            final_score = data_score * 75.0 + candidate.topic_score * 15.0 + contact_score * 10.0
            risks = []
            if candidate.topic_score < 0.45:
                risks.append("Topic match is weak and needs manager review.")
            if not candidate.has_public_contact:
                risks.append("No public business contact found.")
            scored.append(
                ScoredCandidate(
                    key=candidate.key,
                    platform=candidate.platform,
                    normalized_views=normalized_views,
                    normalized_engagement=normalized_engagement,
                    normalized_followers=normalized_followers,
                    topic_score=candidate.topic_score,
                    data_performance_score=data_score,
                    contactability_score=contact_score,
                    final_score=final_score,
                    reasons=[
                        "Ranked mainly by recent views, engagement rate, and follower count.",
                        "Compared within the same platform batch.",
                    ],
                    risks=risks,
                )
            )
    return sorted(scored, key=lambda item: item.final_score, reverse=True)
