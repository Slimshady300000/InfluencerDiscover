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
    follower_label: str | None = None,
) -> DueDiligenceCard:
    normalized_content_titles = [title.strip() for title in content_titles if title.strip()]
    representative_content = (
        " | ".join(normalized_content_titles[:5])
        if normalized_content_titles
        else "暂无已保存的代表内容。"
    )
    risk_text = " | ".join(_localize_risk(risk) for risk in risks) if risks else "已保存数据中暂无明显风险。"
    followers = follower_label or f"{follower_count:,}"
    recommendation = (
        f"{creator_name} 建议进入人工复核：{platform} 账号评分 {score:.1f}，"
        f"粉丝数 {followers}。"
    )
    return DueDiligenceCard(
        creator_name=creator_name,
        recommendation=recommendation,
        representative_content=representative_content,
        data_highlights=f"粉丝数：{followers}。评分：{score:.1f}。",
        risks=risk_text,
        suggested_contact=contact or "如果主页可见私信入口，可优先使用公开私信联系。",
    )


def _localize_risk(risk: str) -> str:
    return {
        "No recent sponsored content found.": "近期赞助内容信息不足。",
        "Topic match is weak and needs manager review.": "话题匹配度偏弱，需要人工复核。",
        "No public business contact found.": "未找到公开商务联系方式。",
    }.get(risk, risk)
