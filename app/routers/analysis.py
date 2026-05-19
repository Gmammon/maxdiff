import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO

from ..database import get_db
from ..models import Project, Design, Respondent, Response
from ..schemas import AnalysisOut, CountModelOut, RespondentOut, FilterRequest
from ..algorithms import mle_estimate, count_model

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _get_responses(db: Session, project_id: str, min_consistency: float = None):
    """获取项目下所有作答记录"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    items = json.loads(project.items_json)

    # 获取受访者
    query = db.query(Respondent).filter(
        Respondent.project_id == project_id, Respondent.status == "completed"
    )
    respondents = query.all()

    # 过滤一致性
    if min_consistency is not None:
        respondents = [
            r
            for r in respondents
            if r.consistency_score is not None and r.consistency_score >= min_consistency
        ]

    # 获取所有作答
    all_responses = []
    for resp in respondents:
        responses = (
            db.query(Response)
            .filter(Response.respondent_id == resp.id, Response.is_duplicate == False)
            .all()
        )
        for r in responses:
            all_responses.append(
                {
                    "items": json.loads(r.items_shown_json),
                    "best": r.best_item,
                    "worst": r.worst_item,
                }
            )

    return project, items, respondents, all_responses


@router.get("/{project_id}", response_model=AnalysisOut)
def get_analysis(
    project_id: str,
    min_consistency: float = Query(None),
    db: Session = Depends(get_db),
):
    project, items, respondents, all_responses = _get_responses(
        db, project_id, min_consistency
    )

    if len(all_responses) < 5:
        raise HTTPException(400, "作答数据不足（至少需要 5 条记录）")

    result = mle_estimate(all_responses, items)
    if result is None:
        raise HTTPException(500, "MLE 估计失败")

    # 一致性统计
    consistency = None
    if respondents:
        scores = [r.consistency_score for r in respondents if r.consistency_score is not None]
        if scores:
            consistency = {
                "mean": round(sum(scores) / len(scores), 3),
                "min": round(min(scores), 3),
                "max": round(max(scores), 3),
                "n_with_score": len(scores),
            }

    return AnalysisOut(
        project_id=project_id,
        respondent_count=len(respondents),
        response_count=len(all_responses),
        items=items,
        utilities=result["utilities"],
        scores=result["scores"],
        standard_errors=result["standard_errors"],
        log_likelihood=result["log_likelihood"],
        rlh=result["rlh"],
        random_rlh=result["random_rlh"],
        rlh_ratio=result["rlh_ratio"],
        iterations=result["iterations"],
        converged=result["converged"],
        consistency=consistency,
    )


@router.get("/{project_id}/count", response_model=CountModelOut)
def get_count_model(project_id: str, db: Session = Depends(get_db)):
    project, items, respondents, all_responses = _get_responses(db, project_id)
    if len(all_responses) < 1:
        raise HTTPException(400, "没有作答数据")
    result = count_model(all_responses, items)
    return CountModelOut(**result)


@router.get("/{project_id}/respondents", response_model=list[RespondentOut])
def get_respondents(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")

    design = (
        db.query(Design)
        .filter(Design.project_id == project_id)
        .order_by(Design.created_at.desc())
        .first()
    )
    tasks = json.loads(design.tasks_json) if design else []

    respondents = (
        db.query(Respondent)
        .filter(Respondent.project_id == project_id)
        .order_by(Respondent.started_at.desc())
        .all()
    )
    return [
        RespondentOut(
            id=r.id,
            status=r.status,
            current_task=r.current_task_number,
            total_tasks=len(tasks),
            consistency_score=r.consistency_score,
            started_at=r.started_at.isoformat(),
        )
        for r in respondents
    ]


@router.post("/{project_id}/filter", response_model=AnalysisOut)
def filter_analysis(project_id: str, data: FilterRequest, db: Session = Depends(get_db)):
    return get_analysis(project_id, min_consistency=data.min_consistency, db=db)


@router.get("/{project_id}/export")
def export_csv(project_id: str, db: Session = Depends(get_db)):
    project, items, respondents, all_responses = _get_responses(db, project_id)

    # 获取所有原始记录
    rows = []
    for resp in respondents:
        responses = (
            db.query(Response)
            .filter(Response.respondent_id == resp.id)
            .order_by(Response.task_number)
            .all()
        )
        for r in responses:
            items_shown = json.loads(r.items_shown_json)
            rows.append(
                f'{resp.id},{r.task_number},"{"|".join(items_shown)}","{r.best_item}","{r.worst_item}",{1 if r.is_duplicate else 0}'
            )

    csv_content = "respondent_id,task_num,items_shown,best,worst,is_duplicate\n" + "\n".join(rows)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=maxdiff_{project_id}.csv"},
    )
