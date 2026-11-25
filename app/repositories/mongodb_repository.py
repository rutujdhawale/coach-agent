import logging
from typing import List, Optional

from app.config.settings import get_settings
from app.repositories.base import get_db

logger = logging.getLogger(__name__)

_DEFAULT_STUDENTS = {
    "student_1": {
        "_id": "student_1",
        "name": "Demo Student",
        "grade": 8,
        "curriculum": "General",
        "weak_topics": ["Algebra", "Organic Chemistry"],
    },
    "lk_g7_kavindu": {
        "_id": "lk_g7_kavindu",
        "name": "Kavindu Perera",
        "grade": 7,
        "school": "Ananda College, Colombo 10",
        "curriculum": "Sri Lanka National Curriculum (Grade 7)",
        "medium": "English",
        "weak_topics": [
            "Fractions & Algebra",
            "Science - Matter & Energy",
            "Sinhala Grammar",
        ],
    },
}

_DEFAULT_EXAM_HISTORY = {
    "student_1": [
        {
            "exam_id": "exam_101",
            "date": "2026-10-15",
            "scores": {"Algebra": 48, "Geometry": 82, "Organic Chemistry": 54, "Physics": 76},
        },
        {
            "exam_id": "exam_102",
            "date": "2026-11-01",
            "scores": {"Algebra": 52, "Geometry": 85, "Organic Chemistry": 58, "Physics": 80},
        },
    ],
    "lk_g7_kavindu": [
        {
            "exam_id": "lk_2026_term1",
            "term": "Term 1 Test",
            "date": "2026-03-20",
            "scores": {
                "Fractions & Algebra": 44,
                "Geometry": 72,
                "Science - Matter & Energy": 49,
                "English Language": 78,
                "History (Sri Lanka)": 68,
                "ICT": 84,
                "Sinhala Grammar": 51,
            },
        },
        {
            "exam_id": "lk_2026_term2",
            "term": "Term 2 Test",
            "date": "2026-07-15",
            "scores": {
                "Fractions & Algebra": 52,
                "Geometry": 76,
                "Science - Matter & Energy": 55,
                "English Language": 81,
                "History (Sri Lanka)": 74,
                "ICT": 88,
                "Sinhala Grammar": 56,
            },
        },
    ],
}


_PRACTICE_ATTEMPTS: dict[str, list[dict]] = {}
_STUDY_PLANS: dict[str, list[dict]] = {}


def _is_placeholder_mongo() -> bool:
    uri = get_settings().MONGODB_URI
    return not uri or "user:pass@cluster.mongodb.net" in uri


class StudentRepository:
    def __init__(self):
        self.collection_name = "students"

    async def get_student_by_id(self, student_id: str) -> Optional[dict]:
        if not _is_placeholder_mongo():
            try:
                db = await get_db()
                student = await db[self.collection_name].find_one({"_id": student_id})
                if student is not None:
                    return student
            except Exception as exc:
                logger.warning("MongoDB unavailable (%s); using sample student data.", exc)
        return _DEFAULT_STUDENTS.get(
            student_id,
            {"_id": student_id, "name": f"Student {student_id}", "weak_topics": ["Algebra"]},
        )

    async def get_exam_history(self, student_id: str) -> List[dict]:
        if not _is_placeholder_mongo():
            try:
                db = await get_db()
                cursor = db["exam_history"].find({"student_id": student_id})
                docs = await cursor.to_list(length=100)
                if docs:
                    return docs
            except Exception as exc:
                logger.warning("MongoDB unavailable (%s); using sample exam history.", exc)
        return _DEFAULT_EXAM_HISTORY.get(student_id, _DEFAULT_EXAM_HISTORY["student_1"])

    async def get_weak_topics(self, student_id: str) -> List[str]:
        student = await self.get_student_by_id(student_id)
        if not student:
            return []
        return student.get("weak_topics", [])

    async def update_weak_topics(self, student_id: str, weak_topics: List[str]) -> dict:
        if not _is_placeholder_mongo():
            try:
                db = await get_db()
                await db[self.collection_name].update_one(
                    {"_id": student_id},
                    {"$set": {"weak_topics": weak_topics}},
                    upsert=True,
                )
            except Exception as exc:
                logger.warning("MongoDB unavailable (%s); updating in-memory student.", exc)
        if student_id not in _DEFAULT_STUDENTS:
            _DEFAULT_STUDENTS[student_id] = {"_id": student_id, "name": f"Student {student_id}", "weak_topics": []}
        _DEFAULT_STUDENTS[student_id]["weak_topics"] = list(weak_topics)
        return {"student_id": student_id, "weak_topics": list(weak_topics)}

    async def record_practice_attempt(
        self, student_id: str, question_id: str, topic: str, is_correct: bool
    ) -> dict:
        attempt = {
            "student_id": student_id,
            "question_id": question_id,
            "topic": topic,
            "correct": is_correct,
        }
        if not _is_placeholder_mongo():
            try:
                db = await get_db()
                await db["practice_attempts"].insert_one(dict(attempt))
            except Exception as exc:
                logger.warning("MongoDB unavailable (%s); storing attempt in memory.", exc)
        _PRACTICE_ATTEMPTS.setdefault(student_id, []).append(attempt)
        return attempt

    async def save_study_plan(self, student_id: str, topic: str, tasks: List[str]) -> dict:
        plan = {"student_id": student_id, "topic": topic, "tasks": list(tasks)}
        if not _is_placeholder_mongo():
            try:
                db = await get_db()
                await db["study_plans"].insert_one(dict(plan))
            except Exception as exc:
                logger.warning("MongoDB unavailable (%s); storing study plan in memory.", exc)
        _STUDY_PLANS.setdefault(student_id, []).append(plan)
        return plan
