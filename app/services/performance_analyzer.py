from typing import List

class PerformanceAnalyzer:
    @staticmethod
    def calculate_topic_scores(exam_history: List[dict]):
        """Logic to analyze scores per topic."""
        # Mock logic for deterministic calculation
        scores = {}
        for exam in exam_history:
            for topic, score in exam.get("scores", {}).items():
                if topic not in scores:
                    scores[topic] = []
                scores[topic].append(score)

        return {topic: sum(s)/len(s) for topic, s in scores.items()}

    @staticmethod
    def identify_weak_areas(topic_scores: dict, threshold: float = 60.0):
        """Returns topics below the threshold."""
        return [topic for topic, avg in topic_scores.items() if avg < threshold]
