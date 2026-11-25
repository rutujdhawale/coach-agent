from typing import List, Dict
from app.services.performance_analyzer import PerformanceAnalyzer

class RecommendationEngine:
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()

    async def generate_recommendations(self, exam_history: List[dict]) -> Dict[str, str]:
        topic_scores = self.analyzer.calculate_topic_scores(exam_history)
        weak_topics = self.analyzer.identify_weak_areas(topic_scores)

        recommendations = {}
        for topic in weak_topics:
            recommendations[topic] = f"Schedule focused revision sessions for {topic}."

        return recommendations