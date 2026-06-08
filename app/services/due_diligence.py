from dataclasses import dataclass


@dataclass(frozen=True)
class DueDiligenceCard:
    creator_name: str
    recommendation: str
    representative_content: str
    data_highlights: str
    risks: str
    suggested_contact: str


def build_due_diligence_card(
    creator_name: str,
    platform: str,
    follower_count: int,
    score: float,
    content_titles: list[str],
    contact: str,
    risks: list[str],
) -> DueDiligenceCard:
    normalized_content_titles = [title.strip() for title in content_titles if title.strip()]
    representative_content = (
        " | ".join(normalized_content_titles[:5])
        if normalized_content_titles
        else "No recent content samples stored."
    )
    risk_text = " | ".join(risks) if risks else "No obvious risk found in stored data."
    recommendation = (
        f"{creator_name} is recommended for manager review because the {platform} account "
        f"has a score of {score:.1f} and {follower_count:,} followers."
    )
    return DueDiligenceCard(
        creator_name=creator_name,
        recommendation=recommendation,
        representative_content=representative_content,
        data_highlights=f"Followers: {follower_count:,}. Score: {score:.1f}.",
        risks=risk_text,
        suggested_contact=contact or "Use public DM entry if visible on the profile.",
    )
