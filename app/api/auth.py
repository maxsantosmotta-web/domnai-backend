from fastapi import APIRouter, Depends

from app.auth import require_authenticated_user
from app.api.admin import bootstrap_owner_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def auth_status(session: dict = Depends(require_authenticated_user)):
    return {
        "status": "ok",
        "authenticated": True,
        "userId": session.get("sub"),
        "sessionId": session.get("sid"),
    }


@router.post("/bootstrap-owner")
def bootstrap_owner(session: dict = Depends(require_authenticated_user)):
    return bootstrap_owner_admin(session)
