import base64

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


def _decode_clerk_frontend_api(publishable_key: str) -> str | None:
    try:
        encoded = publishable_key.split("_", 2)[2]
        encoded += "=" * (-len(encoded) % 4)
        return base64.b64decode(encoded).decode("utf-8").rstrip("$")
    except (IndexError, ValueError, UnicodeDecodeError):
        return None


@router.get("/public")
def public_config():
    if not settings.clerk_publishable_key:
        raise HTTPException(status_code=503, detail="Clerk não configurado.")

    return {
        "clerkPublishableKey": settings.clerk_publishable_key,
        "clerkKeyEnvironment": "production" if settings.clerk_publishable_key.startswith("pk_live_") else "development",
        "clerkKeySource": settings.clerk_publishable_key_source,
        "clerkFrontendApi": _decode_clerk_frontend_api(settings.clerk_publishable_key),
        "applicationOrigin": "https://domnai.iattomassist.com.br",
    }
