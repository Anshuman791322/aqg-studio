"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.endpoints import assessments, auth, documents, questions, version

api_v1_router = APIRouter()

# Include endpoint routers
api_v1_router.include_router(version.router, tags=["system"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(auth.router, tags=["auth"])
api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(assessments.router, tags=["assessments"])
api_v1_router.include_router(questions.router, tags=["questions"])


