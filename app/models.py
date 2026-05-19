import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


def gen_id():
    return uuid.uuid4().hex[:12]


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(12), primary_key=True, default=gen_id)
    name = Column(String(200), nullable=False)
    items_json = Column(Text, nullable=False)  # JSON array of item names
    set_size = Column(Integer, nullable=False)
    appearances = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    designs = relationship("Design", back_populates="project", cascade="all, delete-orphan")
    respondents = relationship("Respondent", back_populates="project", cascade="all, delete-orphan")


class Design(Base):
    __tablename__ = "designs"

    id = Column(String(12), primary_key=True, default=gen_id)
    project_id = Column(String(12), ForeignKey("projects.id"), nullable=False)
    tasks_json = Column(Text, nullable=False)  # JSON: [[item, ...], ...]
    duplicate_pairs_json = Column(Text, default="[]")  # JSON: [{original, duplicate}]
    seed = Column(Integer)
    metrics_json = Column(Text, default="{}")  # JSON: quality metrics
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="designs")
    respondents = relationship("Respondent", back_populates="design")


class Respondent(Base):
    __tablename__ = "respondents"

    id = Column(String(12), primary_key=True, default=gen_id)
    project_id = Column(String(12), ForeignKey("projects.id"), nullable=False)
    design_id = Column(String(12), ForeignKey("designs.id"), nullable=False)
    current_task_number = Column(Integer, default=0)
    status = Column(String(20), default="in_progress")  # in_progress, completed
    consistency_score = Column(Float, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="respondents")
    design = relationship("Design", back_populates="respondents")
    responses = relationship("Response", back_populates="respondent", cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"

    id = Column(String(12), primary_key=True, default=gen_id)
    respondent_id = Column(String(12), ForeignKey("respondents.id"), nullable=False)
    task_number = Column(Integer, nullable=False)
    items_shown_json = Column(Text, nullable=False)  # JSON: [item, ...]
    best_item = Column(String(500), nullable=False)
    worst_item = Column(String(500), nullable=False)
    is_duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    respondent = relationship("Respondent", back_populates="responses")
