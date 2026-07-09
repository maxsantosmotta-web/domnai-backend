from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import DecisionAnalysisRequest
from app.services import generate_initial_analysis, get_decision_categories

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DomnAI — plataforma de apoio à decisão.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "slogan": "Transforme escolhas em resultados com inteligência.",
        "proposal": "Plataforma de apoio à decisão baseada em análises textuais.",
        "phase": "MVP Backend",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/api/decisions/categories")
def decision_categories():
    return {
        "status": "ok",
        "categories": get_decision_categories(),
    }


@app.post("/api/decisions/analyze")
def analyze_decision(payload: DecisionAnalysisRequest):
    return {
        "status": "ok",
        "app": settings.app_name,
        "analysis": generate_initial_analysis(payload),
    }
