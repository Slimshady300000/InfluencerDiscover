from redis import Redis
from rq import Queue

from app.config import get_settings


def get_queue_name() -> str:
    return "influencer-search"


def get_queue() -> Queue:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    return Queue(get_queue_name(), connection=redis)
