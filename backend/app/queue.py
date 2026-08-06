import os

from redis import Redis
from rq import Queue


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://redis:6379/0",
)


redis_connection = Redis.from_url(
    REDIS_URL,
    decode_responses=False,
)


processing_queue = Queue(
    name="csv-processing",
    connection=redis_connection,
    default_timeout=300,
)


def check_redis_connection() -> bool:
    """
    Verify that the application can communicate with Redis.
    """
    return bool(redis_connection.ping())
