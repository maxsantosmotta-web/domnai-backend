from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.chat import router as chat_router
from app.api.config import router as config_router
from app.api.database import router as database_router
from app.api.decisions import router as decisions_router
from app.api.health import router as health_router
from app.api.library import router as library_router
from app.api.profile import router as profile_router
from app.api.trash import router as trash_router
from app.config import settings
from app.database import Base, get_engine, is_database_configured

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DomnAI — plataforma de apoio à decisão.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://domnai.iattomassist.com.br",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def initialize_database_tables() -> None:
    if not is_database_configured():
        return

    from app import models  # noqa: F401

    engine = get_engine()
    if engine is not None:
        Base.metadata.create_all(bind=engine)


app.include_router(health_router)
app.include_router(config_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(decisions_router)
app.include_router(database_router)
app.include_router(library_router)
app.include_router(trash_router)
app.include_router(profile_router)
app.include_router(billing_router)

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "message": "Frontend ainda não compilado.",
        }
