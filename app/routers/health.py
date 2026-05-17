from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Website health check.
    """
    return {"status": "ok"}
