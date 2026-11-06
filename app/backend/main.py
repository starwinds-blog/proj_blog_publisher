import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.backend.api import blog
from app.backend.db.database import Base, engine, get_db
from app.backend.models.story_log import StoryAuditLog  # noqa: F401
from app.backend.services.blog_service import get_dashboard_overview

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Story-to-Blog Publisher Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(blog.router, prefix="/api/blog", tags=["blog"])


@app.get("/api/overview")
def read_overview(db: Session = Depends(get_db)):
    return get_dashboard_overview(db)


web_dist = os.path.join(current_dir, "../web/dist")
if os.path.isdir(web_dist):
    assets_dir = os.path.join(web_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        file_path = os.path.join(web_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(web_dist, "index.html"))
else:
    @app.get("/")
    def read_root():
        return {"message": "Welcome to AI Story-to-Blog Publisher Dashboard API"}
