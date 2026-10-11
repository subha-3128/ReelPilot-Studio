from fastapi import APIRouter
from app.api.endpoints import assets, studio, drafts, publishing, settings, media

api_router = APIRouter()
api_router.include_router(assets.router)
api_router.include_router(studio.router)
api_router.include_router(drafts.router)
api_router.include_router(publishing.router)
api_router.include_router(settings.router)
api_router.include_router(media.router)
