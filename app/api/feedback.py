from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select, update

from app.api.admin import _has_persisted_admin_access
from app.auth import require_authenticated_user
from app.database import session_scope
from app.models import UserFeedback, UserProfile

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

CATEGORY_LABELS = {
    "suggestion": "Sugestão",
    "problem": "Problema",
    "praise": "Elogio",
}

STATUS_LABELS = {
    "received": "Recebido",
    "reviewing": "Em análise",
    "resolved": "Resolvido",
}


class FeedbackPayload(BaseModel):
    category: Literal["suggestion", "problem", "praise"]
    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=3, max_length=120)
    message: str = Field(min_length=10, max_length=2000)


def _serialize(item: UserFeedback, user_name: str = "") -> dict:
    return {
        "id": item.id,
        "userId": item.user_id,
        "userName": user_name,
        "category": item.category,
        "categoryLabel": CATEGORY_LABELS.get(item.category, item.category),
        "rating": item.rating,
        "title": item.title,
        "message": item.message,
        "status": item.status,
        "statusLabel": STATUS_LABELS.get(item.status, item.status),
        "createdAt": item.created_at.isoformat(),
    }


def _require_admin(session: dict) -> str:
    user_id = str(session.get("sub") or "").strip()
    if not user_id or not _has_persisted_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Acesso administrativo não autorizado.")
    return user_id


@router.get("/admin")
def list_admin_feedbacks(
    limit: int = Query(default=200, ge=1, le=500),
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)

    with session_scope() as db:
        items = list(
            db.scalars(
                select(UserFeedback)
                .where(UserFeedback.admin_hidden_at.is_(None))
                .order_by(UserFeedback.created_at.desc())
                .limit(limit)
            ).all()
        )

        summary_row = db.execute(
            select(
                func.count(UserFeedback.id).label("total"),
                func.sum(case((UserFeedback.category == "suggestion", 1), else_=0)).label("suggestions"),
                func.sum(case((UserFeedback.category == "problem", 1), else_=0)).label("problems"),
                func.sum(case((UserFeedback.category == "praise", 1), else_=0)).label("praises"),
                func.avg(UserFeedback.rating).label("average"),
            )
        ).one()

        user_ids = {item.user_id for item in items}
        profiles = {
            profile.user_id: profile.full_name
            for profile in db.scalars(
                select(UserProfile).where(UserProfile.user_id.in_(user_ids))
            ).all()
        } if user_ids else {}

        return {
            "items": [_serialize(item, profiles.get(item.user_id, "")) for item in items],
            "visibleTotal": len(items),
            "summary": {
                "total": int(summary_row.total or 0),
                "suggestions": int(summary_row.suggestions or 0),
                "problems": int(summary_row.problems or 0),
                "praises": int(summary_row.praises or 0),
                "average": float(summary_row.average or 0),
            },
        }


@router.delete("/admin")
def hide_all_admin_feedbacks(
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)
    hidden_at = datetime.now(timezone.utc)

    with session_scope() as db:
        result = db.execute(
            update(UserFeedback)
            .where(UserFeedback.admin_hidden_at.is_(None))
            .values(admin_hidden_at=hidden_at)
        )
        return {
            "hidden": True,
            "hiddenCount": int(result.rowcount or 0),
        }


@router.delete("/admin/{feedback_id}")
def hide_admin_feedback(
    feedback_id: str,
    session: dict = Depends(require_authenticated_user),
):
    _require_admin(session)

    with session_scope() as db:
        item = db.get(UserFeedback, feedback_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Feedback não encontrado.")

        if item.admin_hidden_at is None:
            item.admin_hidden_at = datetime.now(timezone.utc)

        return {
            "hidden": True,
            "feedbackId": item.id,
        }


@router.get("")
def list_user_feedbacks(
    limit: int = Query(default=100, ge=1, le=200),
    session: dict = Depends(require_authenticated_user),
):
    user_id = str(session.get("sub") or "").strip()
    with session_scope() as db:
        items = list(
            db.scalars(
                select(UserFeedback)
                .where(UserFeedback.user_id == user_id)
                .order_by(UserFeedback.created_at.desc())
                .limit(limit)
            ).all()
        )
        profile = db.get(UserProfile, user_id)
        user_name = profile.full_name if profile else ""
        return {
            "items": [_serialize(item, user_name) for item in items],
            "total": len(items),
        }


@router.post("", status_code=201)
def create_user_feedback(
    payload: FeedbackPayload,
    session: dict = Depends(require_authenticated_user),
):
    user_id = str(session.get("sub") or "").strip()
    title = payload.title.strip()
    message = payload.message.strip()

    if len(title) < 3:
        raise HTTPException(status_code=400, detail="Informe um título com pelo menos 3 caracteres.")
    if len(message) < 10:
        raise HTTPException(status_code=400, detail="Descreva seu feedback com pelo menos 10 caracteres.")

    with session_scope() as db:
        item = UserFeedback(
            user_id=user_id,
            category=payload.category,
            rating=payload.rating,
            title=title,
            message=message,
            status="received",
        )
        db.add(item)
        db.flush()

        profile = db.get(UserProfile, user_id)
        return {
            "saved": True,
            "feedback": _serialize(item, profile.full_name if profile else ""),
        }
