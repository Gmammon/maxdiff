from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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

# 模板
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/survey/{project_id}")
def survey_page(request: Request, project_id: str):
    return templates.TemplateResponse(
        "index.html", {"request": request, "project_id": project_id, "page": "survey"}
    )
