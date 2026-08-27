from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.observability.telemetry import setup_telemetry
from permit_pilot_core.seeds import ensure_seeded
from permit_pilot_api.clerk_accounts import ensure_cloud_clerks
from permit_pilot_api.config import cors_origins, gcp_project_id, seed_on_startup
from permit_pilot_api.routes import activity, agents, auth_routes, cases, config, dashboard, intake, nyc, orchestrate, tasks, workflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    store = FirestoreStore(project_id=gcp_project_id())
    engine = DistributionEngine()
    app.state.store = store
    app.state.engine = engine
    ensure_cloud_clerks(store)
    if seed_on_startup():
        await ensure_seeded(store, engine)
    yield


app = FastAPI(title="Permit Pilot API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


app.include_router(auth_routes.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(intake.router, prefix="/api")
app.include_router(nyc.router, prefix="/api")
app.include_router(workflow.router, prefix="/api")
app.include_router(orchestrate.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(agents.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


_static_root = os.environ.get("STATIC_ROOT")
if _static_root and Path(_static_root).is_dir():
    assets_dir = Path(_static_root) / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    _SPA_ENTRY = Path(_static_root) / "app.html"
    _LANDING_ENTRY = Path(_static_root) / "index.html"
    _SPA_PREFIXES = ("login", "dashboard", "activity", "tasks", "permits", "agents", "cases")

    def _spa_entry_for(spa_path: str) -> Path:
        if spa_path in _SPA_PREFIXES or spa_path.startswith("cases/"):
            return _SPA_ENTRY if _SPA_ENTRY.is_file() else _LANDING_ENTRY
        return _LANDING_ENTRY

    @app.get("/{spa_path:path}")
    def spa_fallback(spa_path: str):
        if spa_path.startswith("api/") or spa_path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        candidate = Path(_static_root) / spa_path
        if spa_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_spa_entry_for(spa_path))
