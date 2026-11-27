"""LearningPulse API and production frontend."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LearningPulse")
DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/config")
def public_config():
    return {"supabase_url": os.getenv("SUPABASE_URL", ""), "supabase_publishable_key": os.getenv("SUPABASE_PUBLISHABLE_KEY", "")}

if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

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
