from app.services.scoring import CandidateMetrics, score_batch


def test_score_batch_ranks_data_performance_first():
    candidates = [
        CandidateMetrics(
            key="low",
            platform="youtube",
            follower_count=10000,
            recent_view_count=1000,
            engagement_rate=0.02,
            topic_score=0.95,
            has_public_contact=True,
            has_dm_entry=True,
        ),
        CandidateMetrics(
            key="high",
            platform="youtube",
            follower_count=400000,
            recent_view_count=120000,
            engagement_rate=0.08,
            topic_score=0.75,
            has_public_contact=False,
            has_dm_entry=True,
        ),
    ]
    scored = score_batch(candidates)
    assert scored[0].key == "high"
    assert scored[0].final_score > scored[1].final_score


def test_score_batch_filters_low_topic_match():
    candidates = [
        CandidateMetrics(
            key="off-topic",
            platform="tiktok",
            follower_count=900000,
            recent_view_count=600000,
            engagement_rate=0.12,
            topic_score=0.10,
            has_public_contact=True,
            has_dm_entry=True,
        )
    ]
    scored = score_batch(candidates, minimum_topic_score=0.2)
    assert scored == []
