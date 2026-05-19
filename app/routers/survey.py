import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, Design, Respondent, Response
from ..schemas import SurveyStart, SurveyStartOut, SurveySubmit, SurveySubmitOut, SurveyStatusOut

router = APIRouter(prefix="/api/survey", tags=["survey"])


def _get_design_for_project(db: Session, project_id: str):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    design = (
        db.query(Design)
        .filter(Design.project_id == project_id)
        .order_by(Design.created_at.desc())
        .first()
    )
    if not design:
        raise HTTPException(404, "该项目没有设计")
    return project, design


@router.post("/start", response_model=SurveyStartOut)
def start_survey(data: SurveyStart, db: Session = Depends(get_db)):
    project, design = _get_design_for_project(db, data.project_id)
    tasks = json.loads(design.tasks_json)

    respondent = Respondent(
        project_id=project.id,
        design_id=design.id,
        current_task_number=0,
        status="in_progress",
    )
    db.add(respondent)
    db.commit()

    return SurveyStartOut(
        respondent_id=respondent.id,
        project_id=project.id,
        task_number=1,
        items=tasks[0],
        total_tasks=len(tasks),
    )


@router.get("/{rid}/status", response_model=SurveyStatusOut)
def get_status(rid: str, db: Session = Depends(get_db)):
    resp = db.query(Respondent).filter(Respondent.id == rid).first()
    if not resp:
        raise HTTPException(404, "会话不存在")
    design = db.query(Design).filter(Design.id == resp.design_id).first()
    tasks = json.loads(design.tasks_json)
    return SurveyStatusOut(
        respondent_id=resp.id,
        project_id=resp.project_id,
        status=resp.status,
        current_task=resp.current_task_number,
        total_tasks=len(tasks),
        consistency_score=resp.consistency_score,
    )


@router.post("/{rid}/submit", response_model=SurveySubmitOut)
def submit_response(rid: str, data: SurveySubmit, db: Session = Depends(get_db)):
    resp = db.query(Respondent).filter(Respondent.id == rid).first()
    if not resp:
        raise HTTPException(404, "会话不存在")
    if resp.status == "completed":
        raise HTTPException(400, "问卷已完成")

    design = db.query(Design).filter(Design.id == resp.design_id).first()
    tasks = json.loads(design.tasks_json)
    dup_pairs = json.loads(design.duplicate_pairs_json)

    # 校验 task_number
    if data.task_number != resp.current_task_number + 1:
        raise HTTPException(400, f"任务编号不正确，期望 {resp.current_task_number + 1}")

    task_idx = data.task_number - 1
    if task_idx < 0 or task_idx >= len(tasks):
        raise HTTPException(400, "任务编号超出范围")

    items_shown = tasks[task_idx]

    # 校验 best/worst
    if data.best_item == data.worst_item:
        raise HTTPException(400, "最喜欢和最不喜欢不能是同一个选项")
    if data.best_item not in items_shown:
        raise HTTPException(400, f"选项 '{data.best_item}' 不在当前任务中")
    if data.worst_item not in items_shown:
        raise HTTPException(400, f"选项 '{data.worst_item}' 不在当前任务中")

    # 判断是否为重复任务
    is_duplicate = any(d["duplicate"] == task_idx for d in dup_pairs)

    # 写入作答记录
    response = Response(
        respondent_id=rid,
        task_number=data.task_number,
        items_shown_json=json.dumps(items_shown, ensure_ascii=False),
        best_item=data.best_item,
        worst_item=data.worst_item,
        is_duplicate=is_duplicate,
    )
    db.add(response)
    resp.current_task_number = data.task_number

    # 一致性检查
    if is_duplicate:
        orig_pair = next(d for d in dup_pairs if d["duplicate"] == task_idx)
        orig_task_num = orig_pair["original"] + 1
        orig_response = (
            db.query(Response)
            .filter(Response.respondent_id == rid, Response.task_number == orig_task_num)
            .first()
        )
        if orig_response:
            is_consistent = (
                orig_response.best_item == data.best_item
                and orig_response.worst_item == data.worst_item
            )
            # 更新一致性分数
            _update_consistency(db, resp, dup_pairs)

    # 检查是否完成
    if data.task_number >= len(tasks):
        resp.status = "completed"
        resp.completed_at = datetime.now(timezone.utc)
        _update_consistency(db, resp, dup_pairs)
        db.commit()

        # 生成简单排名
        all_responses = (
            db.query(Response)
            .filter(Response.respondent_id == rid, Response.is_duplicate == False)
            .all()
        )
        scores = {}
        for r in all_responses:
            items = json.loads(r.items_shown_json)
            for it in items:
                scores[it] = scores.get(it, 0)
            scores[r.best_item] += 1
            scores[r.worst_item] -= 1
        ranking = sorted(scores.items(), key=lambda x: -x[1])
        return SurveySubmitOut(
            status="completed",
            ranking=[{"item": item, "score": s} for item, s in ranking],
        )

    db.commit()
    next_task = tasks[data.task_number]  # data.task_number is now the next index
    return SurveySubmitOut(
        status="next",
        task_number=data.task_number + 1,
        items=next_task,
        total_tasks=len(tasks),
    )


def _update_consistency(db: Session, respondent: Respondent, dup_pairs: list):
    """重新计算一致性分数"""
    if not dup_pairs:
        respondent.consistency_score = None
        return

    total = 0
    match = 0
    for dp in dup_pairs:
        orig_num = dp["original"] + 1
        dup_num = dp["duplicate"] + 1
        orig_r = (
            db.query(Response)
            .filter(Response.respondent_id == respondent.id, Response.task_number == orig_num)
            .first()
        )
        dup_r = (
            db.query(Response)
            .filter(Response.respondent_id == respondent.id, Response.task_number == dup_num)
            .first()
        )
        if orig_r and dup_r:
            total += 1
            if orig_r.best_item == dup_r.best_item and orig_r.worst_item == dup_r.worst_item:
                match += 1

    respondent.consistency_score = match / total if total > 0 else None


@router.post("/{rid}/undo")
def undo_response(rid: str, db: Session = Depends(get_db)):
    resp = db.query(Respondent).filter(Respondent.id == rid).first()
    if not resp:
        raise HTTPException(404, "会话不存在")
    if resp.current_task_number <= 0:
        raise HTTPException(400, "已经是第一题，无法撤销")
    if resp.status == "completed":
        raise HTTPException(400, "问卷已完成，无法撤销")

    # 删除最后一条作答
    last_response = (
        db.query(Response)
        .filter(Response.respondent_id == rid, Response.task_number == resp.current_task_number)
        .first()
    )
    if last_response:
        db.delete(last_response)

    resp.current_task_number -= 1
    resp.status = "in_progress"

    # 重新计算一致性
    design = db.query(Design).filter(Design.id == resp.design_id).first()
    dup_pairs = json.loads(design.duplicate_pairs_json)
    _update_consistency(db, resp, dup_pairs)

    db.commit()

    tasks = json.loads(design.tasks_json)
    return {
        "status": "ok",
        "current_task": resp.current_task_number + 1,
        "items": tasks[resp.current_task_number],
        "total_tasks": len(tasks),
    }
