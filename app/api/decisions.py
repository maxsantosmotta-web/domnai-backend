from fastapi import APIRouter

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
def analyze_decision(payload: DecisionAnalysisRequest):
    return {
        "status": "ok",
        "app": "DomnAI",
        "analysis": generate_initial_analysis(payload),
    }
