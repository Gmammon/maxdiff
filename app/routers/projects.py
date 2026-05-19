import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, Design
from ..schemas import ProjectCreate, ProjectOut, DesignOut, DesignMetrics
from ..algorithms import generate_design, insert_duplicate_tasks

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=dict)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    if len(data.items) < 3:
        raise HTTPException(400, "至少需要 3 个选项")
    if data.set_size >= len(data.items):
        raise HTTPException(400, "每轮展示数应小于选项总数")

    # 创建项目
    project = Project(
        name=data.name,
        items_json=json.dumps(data.items, ensure_ascii=False),
        set_size=data.set_size,
        appearances=data.appearances,
    )
    db.add(project)
    db.flush()

    # 生成设计
    result = generate_design(
        data.items, data.set_size, data.appearances, seed=data.seed
    )
    if result is None:
        raise HTTPException(500, "设计生成失败")

    tasks = result["tasks"]
    duplicate_pairs = []

    # 插入重复任务
    if data.add_duplicate:
        tasks, duplicate_pairs = insert_duplicate_tasks(tasks)

    design = Design(
        project_id=project.id,
        tasks_json=json.dumps(tasks, ensure_ascii=False),
        duplicate_pairs_json=json.dumps(duplicate_pairs, ensure_ascii=False),
        seed=result["seed"],
        metrics_json=json.dumps(result["metrics"], ensure_ascii=False),
    )
    db.add(design)
    db.commit()

    return {
        "project_id": project.id,
        "design_id": design.id,
        "tasks": tasks,
        "duplicate_pairs": duplicate_pairs,
        "metrics": result["metrics"],
        "seed": result["seed"],
        "method": result["method"],
    }


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [
        ProjectOut(
            id=p.id,
            name=p.name,
            items=json.loads(p.items_json),
            set_size=p.set_size,
            appearances=p.appearances,
            created_at=p.created_at.isoformat(),
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=dict)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    design = (
        db.query(Design)
        .filter(Design.project_id == project_id)
        .order_by(Design.created_at.desc())
        .first()
    )
    return {
        "id": project.id,
        "name": project.name,
        "items": json.loads(project.items_json),
        "set_size": project.set_size,
        "appearances": project.appearances,
        "created_at": project.created_at.isoformat(),
        "design": {
            "id": design.id,
            "tasks": json.loads(design.tasks_json),
            "duplicate_pairs": json.loads(design.duplicate_pairs_json),
            "metrics": json.loads(design.metrics_json),
            "seed": design.seed,
        }
        if design
        else None,
    }
