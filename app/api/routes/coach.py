import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService
from google.genai import types

from app.agents.performance_coach.agent import performance_coach_agent
from app.config.settings import get_settings
from app.models.schemas import ChatRequest, ChatResponse
from app.security.auth import verify_student_access
from app.security.guardrails import (
    check_user_message,
    enforce_rate_limit,
    sanitize_output,
    validate_student_id,
)
from app.services.telemetry import telemetry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coach", tags=["Performance Coach"])

APP_NAME = "performance_coach"


def _build_session_service():
    db_url = get_settings().SESSION_DB_URL
    if db_url.startswith("sqlite"):
        Path("data").mkdir(parents=True, exist_ok=True)
    try:
        return DatabaseSessionService(db_url=db_url)
    except Exception as exc:
        logger.warning("Falling back to InMemorySessionService (%s).", exc)
        return InMemorySessionService()


_session_service = _build_session_service()
_runner = Runner(
    app_name=APP_NAME,
    agent=performance_coach_agent,
    session_service=_session_service,
)


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(enforce_rate_limit)])
async def coach_chat(request: ChatRequest, authorization: str | None = Header(default=None)):
    validate_student_id(request.student_id)
    verify_student_access(request.student_id, authorization)
    allowed, reason = check_user_message(request.message)
    if not allowed:
        telemetry.record_guardrail_block()
        return ChatResponse(response=reason)

    start = time.perf_counter()
    try:
        session_id = f"session_{request.student_id}"
        session = await _session_service.get_session(
            app_name=APP_NAME,
            user_id=request.student_id,
            session_id=session_id,
        )
        if session is None:
            session = await _session_service.create_session(
                app_name=APP_NAME,
                user_id=request.student_id,
                session_id=session_id,
            )

        user_message = types.Content(
            role="user",
            parts=[types.Part(text=f"[student_id: {request.student_id}]\n{request.message}")],
        )

        final_text = ""
        async for event in _runner.run_async(
            user_id=request.student_id,
            session_id=session.id,
            new_message=user_message,
        ):
            if event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                if text_parts and event.is_final_response():
                    final_text = "\n".join(text_parts)

        telemetry.record_chat((time.perf_counter() - start) * 1000)
        return ChatResponse(response=sanitize_output(final_text or "No response generated."))
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_output(str(e)))
