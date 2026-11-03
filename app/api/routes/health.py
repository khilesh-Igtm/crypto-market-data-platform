from fastapi import APIRouter

router = APIRouter(
    tags=["Health"],
)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Check whether the application is running.
    """

    return {
        "status": "healthy"
    }