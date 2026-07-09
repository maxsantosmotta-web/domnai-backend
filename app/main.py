from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.decisions import router as decisions_router
from app.api.health import router as health_router
from app.config import settings

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
        "availableRoutes": [
            "/health",
            "/api/decisions/categories",
            "/api/decisions/analyze",
        ],
    }


app.include_router(health_router)
app.include_router(decisions_router)
