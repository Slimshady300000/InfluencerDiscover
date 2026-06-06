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


def test_score_batch_handles_all_zero_metrics():
    candidates = [
        CandidateMetrics(
            key="zero-metrics",
            platform="youtube",
            follower_count=0,
            recent_view_count=0,
            engagement_rate=0.0,
            topic_score=0.3,
            has_public_contact=False,
            has_dm_entry=False,
        )
    ]

    scored = score_batch(candidates)

    assert len(scored) == 1
    assert scored[0].normalized_views == 0.0
    assert scored[0].normalized_engagement == 0.0
    assert scored[0].normalized_followers == 0.0


def test_score_batch_normalizes_metrics_within_each_platform():
    candidates = [
        CandidateMetrics(
            key="youtube-top",
            platform="youtube",
            follower_count=100000,
            recent_view_count=50000,
            engagement_rate=0.05,
            topic_score=0.7,
            has_public_contact=True,
            has_dm_entry=True,
        ),
        CandidateMetrics(
            key="youtube-lower",
            platform="youtube",
            follower_count=50000,
            recent_view_count=25000,
            engagement_rate=0.025,
            topic_score=0.7,
            has_public_contact=True,
            has_dm_entry=True,
        ),
        CandidateMetrics(
            key="tiktok-top",
            platform="tiktok",
            follower_count=1000,
            recent_view_count=500,
            engagement_rate=0.01,
            topic_score=0.7,
            has_public_contact=True,
            has_dm_entry=True,
        ),
        CandidateMetrics(
            key="tiktok-lower",
            platform="tiktok",
            follower_count=500,
            recent_view_count=250,
            engagement_rate=0.005,
            topic_score=0.7,
            has_public_contact=True,
            has_dm_entry=True,
        ),
    ]

    scored = {candidate.key: candidate for candidate in score_batch(candidates)}

    assert scored["youtube-top"].normalized_views == 1.0
    assert scored["youtube-top"].normalized_engagement == 1.0
    assert scored["youtube-top"].normalized_followers == 1.0
    assert scored["tiktok-top"].normalized_views == 1.0
    assert scored["tiktok-top"].normalized_engagement == 1.0
    assert scored["tiktok-top"].normalized_followers == 1.0


def test_score_batch_preserves_raw_score_precision_for_close_scores():
    candidates = [
        CandidateMetrics(
            key="lower-raw",
            platform="instagram",
            follower_count=100000,
            recent_view_count=50000,
            engagement_rate=0.05,
            topic_score=0.5001,
            has_public_contact=True,
            has_dm_entry=True,
        ),
        CandidateMetrics(
            key="higher-raw",
            platform="instagram",
            follower_count=100000,
            recent_view_count=50000,
            engagement_rate=0.05,
            topic_score=0.5002,
            has_public_contact=True,
            has_dm_entry=True,
        ),
    ]

    scored = score_batch(candidates)
    scored_by_key = {candidate.key: candidate for candidate in scored}
    expected_higher_score = 75.0 + 0.5002 * 15.0 + 10.0

    assert scored_by_key["higher-raw"].final_score == expected_higher_score
    assert scored[0].key == "higher-raw"
