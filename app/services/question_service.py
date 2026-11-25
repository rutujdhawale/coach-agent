from typing import Dict, List


class QuestionService:
    def __init__(self):
        # In a real system, this would query a question bank database.
        self.question_bank = [
            {"id": "q1", "topic": "Algebra", "text": "Solve 2x + 3 = 7", "options": ["1", "2", "3", "4"], "correct_answer": "2"},
            {"id": "q2", "topic": "Algebra", "text": "What is x^2 * x^3?", "options": ["x^5", "x^6", "x", "1"], "correct_answer": "x^5"},
            {"id": "q3", "topic": "Geometry", "text": "Area of a circle with radius r?", "options": ["pi*r^2", "2*pi*r", "pi*d", "r^2"], "correct_answer": "pi*r^2"},
            {"id": "q4", "topic": "Fractions & Algebra", "text": "Grade 7 Maths: Simplify 3/4 + 2/8", "options": ["1", "5/12", "3/2", "7/8"], "correct_answer": "1"},
            {"id": "q5", "topic": "Fractions & Algebra", "text": "Grade 7 Maths: If 3y - 5 = 10, find y", "options": ["3", "4", "5", "6"], "correct_answer": "5"},
            {"id": "q6", "topic": "Science - Matter & Energy", "text": "Grade 7 Science: Which state of matter has a fixed volume but no fixed shape?", "options": ["Solid", "Liquid", "Gas", "Plasma"], "correct_answer": "Liquid"},
            {"id": "q7", "topic": "Sinhala Grammar", "text": "Grade 7 Sinhala: Which case (විභක්ති) indicates the subject of an active sentence?", "options": ["ප්‍රථමා (Prathama)", "කර්ම (Karma)", "කරණ (Karana)", "සම්ප්‍රදාන (Sampradana)"], "correct_answer": "ප්‍රථමා (Prathama)"},
        ]

    def get_questions_by_topic(self, topic: str, limit: int = 5) -> List[Dict]:
        topic_lower = topic.lower()
        return [
            q for q in self.question_bank
            if q["topic"].lower() == topic_lower or topic_lower in q["topic"].lower()
        ][:limit]

    def evaluate_answer(self, question_id: str, answer: str) -> bool:
        for q in self.question_bank:
            if q["id"] == question_id:
                return q["correct_answer"] == answer
        return False
