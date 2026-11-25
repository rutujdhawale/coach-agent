from fastapi import APIRouter
from app.services.performance_analyzer import PerformanceAnalyzer
from app.services.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/performance", tags=["Performance"])
analyzer = PerformanceAnalyzer()
engine = RecommendationEngine()

@router.post("/analyze")
async def analyze_performance(exam_history: list):
    scores = analyzer.calculate_topic_scores(exam_history)
    weak = analyzer.identify_weak_areas(scores)
    return {"topic_scores": scores, "weak_topics": weak}

@router.post("/recommend")
async def get_recommendations(exam_history: list):
    return await engine.generate_recommendations(exam_history)