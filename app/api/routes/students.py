from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import StudentProgress
from app.repositories.mongodb_repository import StudentRepository
from app.security.guardrails import validate_student_id
from app.services.performance_analyzer import PerformanceAnalyzer

router = APIRouter(prefix="/students", tags=["Students"])
repo = StudentRepository()
analyzer = PerformanceAnalyzer()


class StudentUpdate(BaseModel):
    weak_topics: list = None


@router.get("/{student_id}")
async def get_student(student_id: str):
    validate_student_id(student_id)
    student = await repo.get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/{student_id}/history")
async def get_history(student_id: str):
    validate_student_id(student_id)
    return await repo.get_exam_history(student_id)


@router.get("/{student_id}/weak-topics")
async def get_weak_topics(student_id: str):
    validate_student_id(student_id)
    return await repo.get_weak_topics(student_id)


@router.get("/{student_id}/progress", response_model=StudentProgress)
async def get_progress(student_id: str):
    validate_student_id(student_id)
    history = await repo.get_exam_history(student_id)
    topic_scores = analyzer.calculate_topic_scores(history)
    weak_topics = analyzer.identify_weak_areas(topic_scores)
    avg_score = round(sum(topic_scores.values()) / len(topic_scores), 2) if topic_scores else 0.0

    trend = "stable"
    if len(history) >= 2:
        first_avg = sum(history[0].get("scores", {}).values()) / max(len(history[0].get("scores", {})), 1)
        last_avg = sum(history[-1].get("scores", {}).values()) / max(len(history[-1].get("scores", {})), 1)
        if last_avg > first_avg + 1:
            trend = "improving"
        elif last_avg < first_avg - 1:
            trend = "declining"

    return StudentProgress(
        student_id=student_id,
        exams_taken=len(history),
        average_score=avg_score,
        topic_scores=topic_scores,
        weak_topics=weak_topics,
        trend=trend,
    )
