import json
from typing import Any

from redis import Redis


def check_cancel_status(task_id: str, redis_client: Redis):
    """
    Check if a cancellation mark has appeared in Redis.
    """

    status_data: Any = redis_client.get(f"task:{task_id}")
    if status_data:
        status = json.loads(status_data).get("status")
        if status == "cancelled":
            raise KeyboardInterrupt("Download cancelled by user")
