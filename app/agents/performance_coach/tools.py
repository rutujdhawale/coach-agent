from app.repositories.mongodb_repository import StudentRepository
from app.services.performance_analyzer import PerformanceAnalyzer
from app.services.question_service import QuestionService
from app.services.rag_service import TextbookRagService

repo = StudentRepository()
analyzer = PerformanceAnalyzer()
question_service = QuestionService()
rag_service = TextbookRagService()

_STUDY_RESOURCES = [
    {
        "topic": "Fractions & Algebra",
        "title": "Grade 7 Fractions & Linear Equations Summary",
        "summary": "To add fractions, convert to a common denominator (LCD). For equations like ax + b = c, isolate x in two steps.",
    },
    {
        "topic": "Science - Matter & Energy",
        "title": "Grade 7 States of Matter & Energy Forms",
        "summary": "Solids have fixed shape and volume; liquids have fixed volume but take the container's shape; gases expand to fill volume.",
    },
    {
        "topic": "Sinhala Grammar",
        "title": "Grade 7 Vibhakthi (Cases) Quick Reference",
        "summary": "Prathama (ප්‍රථමා) marks the subject of an active sentence; Karma (කර්ම) marks the direct object.",
    },
    {
        "topic": "Algebra",
        "title": "Exponent & Linear Equation Rules",
        "summary": "Multiply same bases by adding exponents (x^a * x^b = x^(a+b)). Balance equations by applying inverse operations to both sides.",
    },
    {
        "topic": "Geometry",
        "title": "Circles & Polygons Formula Sheet",
        "summary": "Circle area = pi * r^2; circumference = 2 * pi * r.",
    },
]


async def get_exam_history_tool(student_id: str):
    """Retrieves the past exam scores and topic breakdown for a student."""
    return await repo.get_exam_history(student_id)


async def get_weak_topics_tool(student_id: str):
    """Identifies topics where the student scores below the proficiency threshold."""
    history = await repo.get_exam_history(student_id)
    if history:
        scores = analyzer.calculate_topic_scores(history)
        weak = analyzer.identify_weak_areas(scores)
        if weak:
            return weak
    return await repo.get_weak_topics(student_id)


async def generate_recommendations_tool(student_id: str):
    """Generates personalized study recommendations based on weak topics."""
    weak_topics = await get_weak_topics_tool(student_id)
    return [f"Focus on revision and practice problems for: {topic}" for topic in weak_topics]


async def get_practice_questions_tool(topic: str, limit: int = 3):
    """Retrieves practice questions for a given academic topic."""
    questions = question_service.get_questions_by_topic(topic, limit=limit)
    return [
        {
            "id": q["id"],
            "topic": q["topic"],
            "text": q["text"],
            "options": q["options"],
        }
        for q in questions
    ]


async def evaluate_practice_answer_tool(question_id: str, answer: str, student_id: str = ""):
    """Evaluates a student's answer, records the attempt if student_id is given, and returns feedback."""
    is_correct = question_service.evaluate_answer(question_id, answer)
    question = next((q for q in question_service.question_bank if q["id"] == question_id), None)
    if question is None:
        return {"found": False, "correct": False, "message": f"Question {question_id} not found."}
    if student_id:
        await repo.record_practice_attempt(student_id, question_id, question["topic"], is_correct)
    return {
        "found": True,
        "correct": is_correct,
        "topic": question["topic"],
        "correct_answer": question["correct_answer"],
        "feedback": (
            "Correct! Great job."
            if is_correct
            else f"Incorrect. The expected answer is '{question['correct_answer']}'. Review {question['topic']} concepts."
        ),
    }


async def update_weak_topics_tool(student_id: str, weak_topics: list[str]):
    """Updates the student's tracked weak topics after practice or reassessment."""
    return await repo.update_weak_topics(student_id, weak_topics)


async def save_study_plan_tool(student_id: str, topic: str, tasks: list[str]):
    """Saves an actionable study plan for a student and topic."""
    return await repo.save_study_plan(student_id, topic, tasks)


async def search_study_resources_tool(query: str, topic: str = ""):
    """Searches pre-added textbook notes and practice questions by keyword or topic."""
    q_lower = query.strip().lower()
    t_lower = topic.strip().lower()

    matched_notes = rag_service.retrieve(query=query, topic=topic, top_k=3)
    if not matched_notes:
        matched_notes = [
            item
            for item in _STUDY_RESOURCES
            if (not t_lower or t_lower in item["topic"].lower())
            and (
                not q_lower
                or q_lower in item["title"].lower()
                or q_lower in item["summary"].lower()
                or q_lower in item["topic"].lower()
            )
        ][:3]
    matched_questions = [
        {"id": q["id"], "topic": q["topic"], "text": q["text"]}
        for q in question_service.question_bank
        if (not t_lower or t_lower in q["topic"].lower())
        and (not q_lower or q_lower in q["text"].lower() or q_lower in q["topic"].lower())
    ][:3]

    return {"notes": matched_notes, "questions": matched_questions}
