from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.knowledge_bases import router as knowledge_bases_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(knowledge_bases_router)
router.include_router(documents_router)


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "personal-knowledge-hub-api",
    }
