from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.settings import router as settings_router
from app.core.config import settings
from app.core.health import readiness_payload
from app.db.session import SessionLocal
from app.services.auth_service import AuthService
from app.workers.celery_app import recover_queue_state

app = FastAPI(title="DouyinGenerator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live")
def live_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready_health() -> JSONResponse:
    ready, payload = readiness_payload()
    return JSONResponse(status_code=200 if ready else 503, content=payload)


@app.on_event("startup")
def seed_admin_user() -> None:
    db = SessionLocal()
    try:
        AuthService(db).ensure_admin_user()
    finally:
        db.close()
    recover_queue_state()


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
