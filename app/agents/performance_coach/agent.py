from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import FunctionTool
from google.genai import types

from app.agents.performance_coach.prompts import PERFORMANCE_COACH_INSTRUCTION
from app.agents.performance_coach.tools import (
    evaluate_practice_answer_tool,
    generate_recommendations_tool,
    get_exam_history_tool,
    get_practice_questions_tool,
    get_weak_topics_tool,
    save_study_plan_tool,
    search_study_resources_tool,
    update_weak_topics_tool,
)
from app.security.guardrails import check_user_message, sanitize_output
from app.services.llm_router import FallbackLiteLlm


def _guardrail_before_model(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Block prompt-injection or unsafe user messages before calling the LLM."""
    if not llm_request.contents:
        return None
    for content in reversed(llm_request.contents):
        if content.role == "user" and content.parts:
            text = " ".join(p.text for p in content.parts if p.text)
            if text:
                allowed, reason = check_user_message(text)
                if not allowed:
                    return LlmResponse(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text=reason)],
                        )
                    )
            break
    return None


def _guardrail_after_model(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Redact any accidentally leaked secrets from model responses."""
    if not llm_response.content or not llm_response.content.parts:
        return None
    changed = False
    new_parts = []
    for part in llm_response.content.parts:
        if part.text:
            cleaned = sanitize_output(part.text)
            if cleaned != part.text:
                changed = True
                new_parts.append(types.Part(text=cleaned))
            else:
                new_parts.append(part)
        else:
            new_parts.append(part)
    if changed:
        return LlmResponse(
            content=types.Content(role=llm_response.content.role, parts=new_parts)
        )
    return None


def create_performance_coach_agent() -> LlmAgent:
    """
    Factory that builds the Google ADK Performance Coach agent.

    Uses FallbackLiteLlm so the agent talks to free Groq models (primary +
    fallbacks) and optional Gemini fallback transparently, with input/output
    guardrails enforced for both FastAPI and `adk web`.
    """
    model = FallbackLiteLlm()

    tools = [
        FunctionTool(get_exam_history_tool),
        FunctionTool(get_weak_topics_tool),
        FunctionTool(generate_recommendations_tool),
        FunctionTool(get_practice_questions_tool),
        FunctionTool(evaluate_practice_answer_tool),
        FunctionTool(search_study_resources_tool),
        FunctionTool(update_weak_topics_tool),
        FunctionTool(save_study_plan_tool),
    ]

    return LlmAgent(
        name="performance_coach",
        model=model,
        description=(
            "Analyzes student exam history, identifies weak topics, evaluates "
            "practice answers, and generates personalized study recommendations."
        ),
        instruction=PERFORMANCE_COACH_INSTRUCTION,
        tools=tools,
        before_model_callback=_guardrail_before_model,
        after_model_callback=_guardrail_after_model,
    )


# Standard Google ADK entrypoint for `adk web` and `adk run`
root_agent = create_performance_coach_agent()

# Alias for FastAPI routes
performance_coach_agent = root_agent
