import json

from redis.asyncio import Redis


async def get_download_status(
    task_id: str,
    r: Redis,
) -> dict[str, str]:
    """
    Fetch current download status from Redis.
    """

    data = await r.get(f"task:{task_id}")
    if data:
        result_dict: dict[str, str] = json.loads(data)
        return result_dict
    return {"status": "pending"}
