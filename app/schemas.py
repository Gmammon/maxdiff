from pydantic import BaseModel
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    items: list[str]
    set_size: int = 4
    appearances: int = 4
    seed: Optional[int] = None
    add_duplicate: bool = True


class ProjectOut(BaseModel):
    id: str
    name: str
    items: list[str]
    set_size: int
    appearances: int
    created_at: str


class DesignMetrics(BaseModel):
    task_count: int
    item_count: int
    appearance_min: int
    appearance_max: int
    covered_pairs: int
    total_pairs: int
    pair_min: int
    pair_max: int
    max_pair_deviation: int
    d_efficiency: float
    is_bibd: bool


class DesignOut(BaseModel):
    id: str
    tasks: list[list[str]]
    duplicate_pairs: list[dict]
    metrics: DesignMetrics
    seed: int
    method: str


class SurveyStart(BaseModel):
    project_id: str


class SurveyStartOut(BaseModel):
    respondent_id: str
    project_id: str
    task_number: int
    items: list[str]
    total_tasks: int


class SurveySubmit(BaseModel):
    task_number: int
    best_item: str
    worst_item: str


class SurveySubmitOut(BaseModel):
    status: str  # "next" or "completed"
    task_number: Optional[int] = None
    items: Optional[list[str]] = None
    total_tasks: Optional[int] = None
    ranking: Optional[list[dict]] = None  # 当完成时


class SurveyStatusOut(BaseModel):
    respondent_id: str
    project_id: str
    status: str
    current_task: int
    total_tasks: int
    consistency_score: Optional[float] = None


class AnalysisOut(BaseModel):
    project_id: str
    respondent_count: int
    response_count: int
    items: list[str]
    utilities: dict[str, float]
    scores: dict[str, float]
    standard_errors: dict[str, float]
    log_likelihood: float
    rlh: float
    random_rlh: float
    rlh_ratio: float
    iterations: int
    converged: bool
    consistency: Optional[dict] = None


class CountModelOut(BaseModel):
    best_count: dict[str, int]
    worst_count: dict[str, int]
    diff: dict[str, int]
    scores: dict[str, float]


class RespondentOut(BaseModel):
    id: str
    status: str
    current_task: int
    total_tasks: int
    consistency_score: Optional[float] = None
    started_at: str


class FilterRequest(BaseModel):
    min_consistency: float = 0.8
