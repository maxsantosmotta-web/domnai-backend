from fastapi import APIRouter, Depends

from app.auth import require_authenticated_user
from app.schemas import DecisionAnalysisRequest
from app.services import generate_initial_analysis, get_decision_categories

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("/categories")
def decision_categories():
    return {
        "status": "ok",
        "categories": get_decision_categories(),
    }


@router.post("/analyze")
def analyze_decision(
    payload: DecisionAnalysisRequest,
    session: dict = Depends(require_authenticated_user),
):
    return {
        "status": "ok",
        "app": "DomnAI",
        "userId": session.get("sub"),
        "analysis": generate_initial_analysis(payload),
    }
