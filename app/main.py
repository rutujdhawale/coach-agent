from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, coach, performance, questions, students
from app.repositories.base import MongoDB
from app.services.telemetry import telemetry

app = FastAPI(
    title="Examblue Performance Coach API",
    description="Backend-only student performance coach powered by Google ADK and LiteLLM.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    await MongoDB.connect()


@app.on_event("shutdown")
async def shutdown_db_client():
    await MongoDB.close()


app.include_router(auth.router, prefix="/api/v1")
app.include_router(coach.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(questions.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/v1/metrics")
async def get_metrics():
    return telemetry.snapshot()
