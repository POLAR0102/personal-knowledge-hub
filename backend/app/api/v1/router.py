from fastapi import APIRouter

from app.api.v1.agent import router as agent_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.documents import router as documents_router
from app.api.v1.knowledge_bases import router as knowledge_bases_router
from app.api.v1.notes import router as notes_router
from app.api.v1.rag import router as rag_router
from app.api.v1.tags import router as tags_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(knowledge_bases_router)
router.include_router(documents_router)
router.include_router(rag_router)
router.include_router(conversations_router)
router.include_router(agent_router)
router.include_router(notes_router)
router.include_router(tags_router)


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "personal-knowledge-hub-api",
    }
