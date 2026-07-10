from fastapi import APIRouter, Depends

from app.auth import require_authenticated_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def auth_status(session: dict = Depends(require_authenticated_user)):
    return {
        "status": "ok",
        "authenticated": True,
        "userId": session.get("sub"),
        "sessionId": session.get("sid"),
    }
