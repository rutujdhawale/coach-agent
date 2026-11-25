from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    response: str


class StudentProfile(BaseModel):
    student_id: str
    name: str
    weak_topics: List[str] = Field(default_factory=list)


class StudentProgress(BaseModel):
    student_id: str
    exams_taken: int
    average_score: float
    topic_scores: Dict[str, float]
    weak_topics: List[str]
    trend: str
