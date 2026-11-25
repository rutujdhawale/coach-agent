import logging
from typing import Any, AsyncGenerator, List, Optional

from app.config.settings import get_settings  # noqa: I001 - ensures LITELLM_LOCAL_MODEL_COST_MAP is set before litellm import
from app.services.telemetry import telemetry

import litellm
from google.adk.models.base_llm import BaseLlm, LlmCapabilities
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from pydantic import PrivateAttr

logger = logging.getLogger(__name__)

_PLACEHOLDER_KEYS = {"", "your_gemini_api_key_here", "your_groq_api_key_here", "your_key"}


def _api_key_for_model(model_name: str, settings: Any) -> Optional[str]:
    """Return the configured API key for a LiteLLM model string, or None if unset."""
    lower = model_name.lower()
    if lower.startswith("groq/"):
        key = settings.GROQ_API_KEY
    elif lower.startswith("gemini/"):
        key = settings.GEMINI_API_KEY
    else:
        return None
    return None if key in _PLACEHOLDER_KEYS else key


def build_model_specs() -> List[tuple[str, Optional[str]]]:
    """Build ordered (model_name, api_key) pairs for primary + fallback models."""
    settings = get_settings()
    raw_models = [settings.PRIMARY_MODEL] + [
        m.strip() for m in settings.FALLBACK_MODELS.split(",") if m.strip()
    ]
    specs: List[tuple[str, Optional[str]]] = []
    seen = set()
    for model_name in raw_models:
        if model_name in seen:
            continue
        seen.add(model_name)
        api_key = _api_key_for_model(model_name, settings)
        if model_name.lower.startswith(("groq/", "gemini/")) if False else model_name.lower().startswith(("groq/", "gemini/")) and not api_key:
            continue
        specs.append((model_name, api_key))

    if not specs:
        specs.append((settings.PRIMARY_MODEL, _api_key_for_model(settings.PRIMARY_MODEL, settings)))
    return specs


class FallbackLiteLlm(BaseLlm):
    """Google ADK BaseLlm that tries primary LiteLlm and falls back across alternatives."""

    _candidates: List[LiteLlm] = PrivateAttr(default_factory=list)

    def __init__(self, models: Optional[List[LiteLlm]] = None, **kwargs: Any):
        settings = get_settings()
        candidates = models or [
            LiteLlm(
                model=name,
                max_tokens=settings.MAX_OUTPUT_TOKENS,
                **({"api_key": key} if key else {}),
            )
            for name, key in build_model_specs()
        ]
        super().__init__(model=candidates[0].model, **kwargs)
        self._candidates = candidates

    @property
    def candidates(self) -> List[LiteLlm]:
        return self._candidates

    @property
    def capabilities(self) -> LlmCapabilities:
        return self._candidates[0].capabilities

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        last_error: Optional[Exception] = None

        # Strip prior thought parts so Groq/OpenAI-compatible endpoints do not
        # reject `reasoning_content` on multi-turn tool-call messages.
        cleaned_contents = []
        for content in llm_request.contents or []:
            if content.parts:
                kept_parts = [p for p in content.parts if not getattr(p, "thought", False)]
                if kept_parts:
                    cleaned_contents.append(content.model_copy(update={"parts": kept_parts}))
            else:
                cleaned_contents.append(content)

        for idx, candidate in enumerate(self._candidates):
            yielded_any = False
            req = llm_request.model_copy(
                update={"model": candidate.model, "contents": cleaned_contents}
            )
            try:
                telemetry.record_llm_call()
                async for response in candidate.generate_content_async(req, stream=stream):
                    if response.error_code and not yielded_any:
                        raise RuntimeError(
                            f"Model {candidate.model} returned error "
                            f"{response.error_code}: {response.error_message}"
                        )
                    yielded_any = True
                    yield response
                return
            except Exception as exc:
                last_error = exc
                telemetry.record_llm_error()
                if yielded_any:
                    raise
                if idx + 1 < len(self._candidates):
                    telemetry.record_llm_fallback()
                    logger.warning(
                        "LLM %s failed (%s). Falling back to %s.",
                        candidate.model,
                        exc,
                        self._candidates[idx + 1].model,
                    )
                else:
                    logger.error(
                        "All LLM candidates failed. Last error from %s: %s",
                        candidate.model,
                        exc,
                    )

        if last_error is not None:
            raise last_error
        raise RuntimeError("No LLM candidates are configured.")


class LLMRouter:
    """Direct LiteLLM router with automatic fallback across configured free models."""

    def __init__(self):
        self.model_specs = build_model_specs()
        self.primary_model = self.model_specs[0][0]
        self.fallback_models = [m for m, _ in self.model_specs[1:]]
        self.max_tokens = get_settings().MAX_OUTPUT_TOKENS

    async def completion(self, messages, **kwargs):
        last_error: Optional[Exception] = None
        for model_name, api_key in self.model_specs:
            try:
                call_kwargs = dict(kwargs)
                call_kwargs.setdefault("max_tokens", self.max_tokens)
                if api_key and "api_key" not in call_kwargs:
                    call_kwargs["api_key"] = api_key
                return await litellm.acompletion(
                    model=model_name,
                    messages=messages,
                    **call_kwargs,
                )
            except Exception as exc:
                last_error = exc
                logger.warning("LLMRouter: %s failed (%s), trying next fallback.", model_name, exc)

        if last_error is not None:
            raise last_error
        raise RuntimeError("No LLM models configured in LLMRouter.")
