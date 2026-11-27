"""LearningPulse API and production frontend."""
import os
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from codebase.backend.security.auth import require_coach
from codebase.backend.analytics.snapshot import read_snapshot
from codebase.backend.analytics.workflow import create_report
from codebase.backend.api.dashboard import router as dashboard_router
from codebase.backend.api.analysis_runs import router as analysis_runs_router
from codebase.backend.security.headers import security_headers
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LearningPulse")

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in security_headers().items():
        response.headers.setdefault(name, value)
    return response

app.include_router(dashboard_router)
app.include_router(analysis_runs_router)
DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/config")
def public_config():
    return {"supabase_url": os.getenv("SUPABASE_URL", ""), "supabase_publishable_key": os.getenv("SUPABASE_PUBLISHABLE_KEY", "")}

if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

@app.get("/api/me")
def me(user: dict = Depends(require_coach)):
    return user

@app.get("/api/lessons")
def lessons(user: dict = Depends(require_coach)):
    return sorted(read_snapshot())

@app.get("/api/lessons/{lesson_id}")
def report(lesson_id: str, user: dict = Depends(require_coach)):
    result = create_report(lesson_id, read_snapshot())
    if result is None:
        raise HTTPException(404, "Không có dữ liệu cho bài học")
    return result

@app.get("/{path:path}")
def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404)
    file = (DIST / path).resolve()
    if file.is_relative_to(DIST.resolve()) and file.is_file():
        return FileResponse(file)
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html")
    raise HTTPException(status_code=404, detail="Frontend chưa được build")
