from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin_audit import router as admin_audit_router
from app.api.admin_billing import router as admin_billing_router
from app.api.admin_errors import router as admin_errors_router
from app.api.admin_users import router as admin_users_router
from app.api.artifacts import router as artifacts_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.chat_persistent import router as chat_persistent_router
from app.api.chat_state import router as chat_state_router
from app.api.chat_tasks import router as chat_tasks_router
from app.api.config import router as config_router
from app.api.database import router as database_router
from app.api.decisions import router as decisions_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.library import router as library_router
from app.api.profile import router as profile_router
from app.api.reports import router as reports_router
from app.api.trash import router as trash_router
from app.config import settings
from app.domnai_core.parallel_api_bootstrap import mount_parallel_api
from app.error_monitoring import module_from_path, record_operational_event
from app.services.chat_task_worker import start_chat_task_worker

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
def start_persistent_chat_worker():
    start_chat_task_worker()


@app.middleware("http")
async def monitor_operational_errors(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/admin/errors"):
        return await call_next(request)
    try:
        response = await call_next(request)
    except Exception as exc:
        record_operational_event(
            module=module_from_path(path),
            severity="critical",
            title=type(exc).__name__,
            message=str(exc) or "Falha inesperada sem mensagem detalhada.",
            source="backend",
            path=path,
            method=request.method,
        )
        raise
    if response.status_code >= 500:
        record_operational_event(
            module=module_from_path(path),
            severity="error",
            title=f"Resposta HTTP {response.status_code}",
            message="A rota respondeu com falha interna e foi agrupada automaticamente.",
            source="backend",
            path=path,
            method=request.method,
        )
    return response


app.include_router(health_router)
app.include_router(config_router)
app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(admin_billing_router)
app.include_router(admin_errors_router)
app.include_router(admin_audit_router)
app.include_router(chat_persistent_router)
app.include_router(chat_state_router)
app.include_router(chat_tasks_router)
app.include_router(decisions_router)
app.include_router(database_router)
app.include_router(library_router)
app.include_router(reports_router)
app.include_router(artifacts_router)
app.include_router(trash_router)
app.include_router(profile_router)
app.include_router(billing_router)
app.include_router(feedback_router)

# Desligada por padrão. Reverter a flag remove imediatamente toda a superfície paralela.
mount_parallel_api(app)

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
