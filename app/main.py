from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

from .database import engine, Base
from .routers import projects, survey, analysis

# 创建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MaxDiff 问卷平台", version="2.0")

# 注册路由
app.include_router(projects.router)
app.include_router(survey.router)
app.include_router(analysis.router)

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "templates" / "index.html"


@app.get("/")
def index():
    return FileResponse(INDEX_HTML)


@app.get("/survey/{project_id}")
def survey_page(project_id: str):
    return FileResponse(INDEX_HTML)
