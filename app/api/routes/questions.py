from fastapi import APIRouter
from app.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["Questions"])
service = QuestionService()

@router.get("/by_topic/{topic}")
async def get_questions(topic: str, limit: int = 5):
    return service.get_questions_by_topic(topic, limit)

@router.post("/evaluate")
async def evaluate_answer(question_id: str, answer: str):
    is_correct = service.evaluate_answer(question_id, answer)
    return {"correct": is_correct}