from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/public")
def public_config():
    if not settings.clerk_publishable_key:
        raise HTTPException(status_code=503, detail="Clerk não configurado.")

    return {
        "clerkPublishableKey": settings.clerk_publishable_key,
    }
