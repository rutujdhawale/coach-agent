# Examblue Performance Coach — Detailed Project Explanation

This document explains how the Examblue Performance Coach project is structured, what each important file does, how a request flows through the system, and how to walk someone through the project clearly.

---

## 1. High-Level Overview (The "Elevator Pitch")

Examblue Performance Coach is a **backend-only AI coaching service** for students (with a sample Sri Lankan Grade 7 student profile, `lk_g7_kavindu`). Instead of letting an LLM guess answers or hallucinate scores, the system uses **Google ADK (Agent Development Kit)** to connect an LLM to deterministic Python tools, student exam records, and textbook notes.

Key design goals:
- **Cost-efficient**: Runs on free Groq models (`openai/gpt-oss-120b` primary) with automatic fallback to secondary Groq/Gemini models, plus `MAX_OUTPUT_TOKENS=700` and top-3 RAG retrieval to save tokens.
- **Reliable in dev and prod**: Uses SQLite for persistent ADK chat sessions and MongoDB for student data, with automatic in-memory sample fallbacks when MongoDB is not configured.
- **Safe by default**: Enforces rate limiting, JWT student isolation, prompt-injection filtering, and secret redaction on both the FastAPI API and Google ADK Web UI (`adk web`).

---

## 2. Project Folder & Important Files

### Configuration & Entry Points
- **`app/main.py`**
  - Creates the FastAPI application, enables CORS (for future web/mobile frontends), connects/closes MongoDB on startup/shutdown, mounts all `/api/v1/*` routers, and exposes `/health` and `/api/v1/metrics`.
- **`app/config/settings.py`**
  - Loads environment variables from `.env` using `pydantic-settings`.
  - Sets `LITELLM_LOCAL_MODEL_COST_MAP=True` so LiteLLM does not hang trying to download remote cost maps when offline.
  - Defines `PRIMARY_MODEL`, `FALLBACK_MODELS`, `MAX_OUTPUT_TOKENS` (`700`), `SESSION_DB_URL` (`sqlite+aiosqlite:///./data/sessions.db`), `AUTH_REQUIRED`, `JWT_SECRET`, and `MONGODB_URI`.

### Google ADK Agent (`app/agents/performance_coach/`)
- **`app/agents/performance_coach/__init__.py`**
  - Exports `agent` so `adk web app/agents` automatically discovers `performance_coach`.
- **`app/agents/performance_coach/agent.py`**
  - Builds the `LlmAgent` (`root_agent` / `performance_coach_agent`), attaches `FallbackLiteLlm` as the model, registers all 8 tools, and wires `before_model_callback` and `after_model_callback` for guardrails.
- **`app/agents/performance_coach/prompts.py`**
  - Holds `PERFORMANCE_COACH_INSTRUCTION`, which tells the agent to cite retrieved data, keep answers concise by default (to save tokens), and stay strictly within academic coaching.
- **`app/agents/performance_coach/tools.py`**
  - Defines the 8 tools the LLM can call:
    1. `get_exam_history_tool(student_id)` — fetches past term-test scores.
    2. `get_weak_topics_tool(student_id)` — computes or retrieves topics below threshold.
    3. `generate_recommendations_tool(student_id)` — builds targeted revision tips.
    4. `get_practice_questions_tool(topic, limit)` — fetches practice questions for a topic.
    5. `evaluate_practice_answer_tool(question_id, answer, student_id)` — grades an answer and logs the attempt.
    6. `search_study_resources_tool(query, topic)` — searches pre-added textbook notes via `TextbookRagService` + question bank.
    7. `update_weak_topics_tool(student_id, weak_topics)` — updates a student's weak topics after practice.
    8. `save_study_plan_tool(student_id, topic, tasks)` — persists a study plan for the student.

### LLM Routing & Fallback (`app/services/llm_router.py`)
- **`build_model_specs()`**
  - Reads `PRIMARY_MODEL` and `FALLBACK_MODELS`, skips any provider whose API key is missing or still a placeholder (e.g., `your_gemini_api_key_here`), and returns an ordered list of `(model_name, api_key)` pairs.
- **`FallbackLiteLlm(BaseLlm)`**
  - Custom Google ADK model wrapper around `LiteLlm`.
  - Strips `thought` parts from prior conversation turns so Groq's OpenAI-compatible API does not reject `reasoning_content` on multi-turn tool calls.
  - Passes `max_tokens=settings.MAX_OUTPUT_TOKENS` to keep responses concise.
  - If the primary model fails or returns an error before streaming content, it logs a warning, updates telemetry, and automatically retries with the next fallback model.
- **`LLMRouter`**
  - Direct async `litellm.acompletion` wrapper with the same fallback chain for any non-ADK service that needs raw completions.

### Business Services (`app/services/`)
- **`app/services/performance_analyzer.py`**
  - Deterministic math (no LLM needed): `calculate_topic_scores` averages scores per topic across exams, and `identify_weak_areas` flags topics below `60.0`.
- **`app/services/recommendation_engine.py`**
  - Uses `PerformanceAnalyzer` to generate deterministic study recommendations per weak topic.
- **`app/services/question_service.py`**
  - In-memory question bank containing Algebra, Geometry, and Sri Lankan Grade 7 questions (`Fractions & Algebra`, `Science - Matter & Energy`, `Sinhala Grammar`), plus `evaluate_answer`.
- **`app/services/rag_service.py` & `data/textbooks/grade7_lk_notes.md`**
  - `TextbookRagService` parses Markdown textbook files under `data/textbooks/` into section chunks (`title`, `topic`, `source`, `content`) and returns the top-k matching chunks by topic and keyword overlap.
- **`app/services/telemetry.py`**
  - Tracks `chat_requests`, `guardrail_blocks`, `llm_calls`, `llm_fallbacks`, `llm_errors`, and average chat latency, exposed via `GET /api/v1/metrics`.

### Data Layer (`app/repositories/`)
- **`app/repositories/base.py`**
  - Manages the Motor (`AsyncIOMotorClient`) connection to MongoDB with a 2-second timeout so unavailable databases fail fast.
- **`app/repositories/mongodb_repository.py`**
  - `StudentRepository` reads/writes `students`, `exam_history`, `practice_attempts`, and `study_plans`.
  - If `MONGODB_URI` is a placeholder or unreachable, it falls back seamlessly to built-in sample data, including `lk_g7_kavindu` (*Kavindu Perera*, Grade 7, *Ananda College, Colombo 10*).

### Security & Guardrails (`app/security/`)
- **`app/security/guardrails.py`**
  - `validate_student_id`: blocks NoSQL injection / invalid characters (`^[a-zA-Z0-9_-]{1,64}$`).
  - `check_user_message`: enforces max length (2000 chars) and blocks prompt-injection attempts (e.g., "ignore previous instructions", "reveal system prompt", persona/role overrides, `### system:` / `<|im_start|>system` delimiter spoofing) and unsafe/off-topic misuse (malware, phishing, exam hacking).
  - `sanitize_output`: redacts any accidentally leaked API keys (`gsk_...`, `AIza...`) or `mongodb://` URIs.
  - `InMemoryRateLimiter`: limits clients to 30 requests per 60 seconds.
- **`app/security/auth.py`**
  - Implements HS256 JWT creation (`create_access_token`) and verification (`verify_access_token`, `verify_student_access`) using Python's built-in `hmac` and `hashlib`.
  - When `AUTH_REQUIRED=false` (default dev mode), requests without a token still work, while any supplied `Bearer` token is strictly verified to match the requested `student_id`. When `AUTH_REQUIRED=true`, a valid `Bearer` token is mandatory.

### REST API Routes (`app/api/routes/`)
- **`coach.py`**: `POST /api/v1/coach/chat` — runs the ADK `Runner` with persistent SQLite sessions (`DatabaseSessionService`), prepending `[student_id: ...]` so the agent always queries the right student.
- **`students.py`**: `GET /api/v1/students/{student_id}`, `/history`, `/weak-topics`, and `/progress` (aggregated averages and improving/stable/declining trend).
- **`performance.py`**: `POST /api/v1/performance/analyze` and `/recommend`.
- **`questions.py`**: `GET /api/v1/questions/by_topic/{topic}` and `POST /api/v1/questions/evaluate`.
- **`auth.py`**: `POST /api/v1/auth/token` — issues a student-scoped Bearer token for testing or client login.

### Testing, Evals, Demo & Docker
- **`tests/test_main.py`**: 11 automated unit/integration tests covering health check, ADK agent setup, `FallbackLiteLlm` fallback, `LLMRouter` fallback, `/coach/chat`, guardrails, secret redaction, Sri Lankan Grade 7 profile/progress, action tools, textbook RAG, JWT auth, `/metrics`, and the offline eval suite.
- **`evals/cases.json` & `evals/run_evals.py`**: Automated evaluation suite testing prompt-injection/misuse blocking, secret redaction, textbook RAG retrieval, and optional live end-to-end LLM responses (`python -m evals.run_evals --live`).
- **`scripts/run_student_demo.py`**: End-to-end demo script that queries `/health`, `/students/lk_g7_kavindu`, `/progress`, and sends a live chat prompt to `/coach/chat`.
- **`Dockerfile`, `docker-compose.yml`, `.dockerignore`**: Containerizes FastAPI (`:8000`), ADK Web UI (`:8001`), and MongoDB (`:27017`).

---

## 3. Step-by-Step Walkthrough of a Request

Suppose a student (`lk_g7_kavindu`) sends:
> *"Check my term test history, tell me my weak topics, and give me 2 practice questions."*

1. **FastAPI (`coach.py`)** validates `student_id`, checks the `Bearer` token (if required/provided), checks the rate limit, and runs `check_user_message`.
2. **Session Service** loads Kavindu's previous conversation from `data/sessions.db` (or creates a new session).
3. **ADK `Runner`** invokes `performance_coach` (`LlmAgent`).
4. **`before_model_callback`** runs the input guardrail again (so `adk web` gets the exact same protection).
5. **Turn 1 (Tool Selection)**: `FallbackLiteLlm` sends the prompt + tool schemas to `groq/openai/gpt-oss-120b`. The model decides to call `get_exam_history_tool("lk_g7_kavindu")`, `get_weak_topics_tool("lk_g7_kavindu")`, and `get_practice_questions_tool("Fractions & Algebra", limit=2)`.
6. **Tool Execution**: Python executes those async functions against `StudentRepository` and `QuestionService` and feeds the JSON results back to the model.
7. **Turn 2 (Final Answer)**: `FallbackLiteLlm` strips any internal `thought` parts from Turn 1, sends the tool results to Groq (falling back to Qwen 3.8 / GPT-OSS-20B / Gemini if needed), and generates a concise coaching reply citing Kavindu's Term 1 & Term 2 scores.
8. **Response**: `after_model_callback` + `sanitize_output` scrub any sensitive patterns, `telemetry` records latency and LLM call counts, and FastAPI returns `{ "response": "..." }`.

---

## 4. How to Explain This Project in 2 Minutes

- **Problem**: Students get raw exam scores, not actionable guidance. Sending entire textbooks to a large LLM on every question is slow and expensive.
- **Solution**: A FastAPI + Google ADK agent that combines **deterministic score analytics**, **8 read/write coaching tools**, and **lightweight textbook RAG** (`data/textbooks/*.md`) with **free Groq LLMs + automatic multi-model fallback**.
- **Why this architecture**:
  - Keeping analytics deterministic (`PerformanceAnalyzer`) prevents math errors.
  - Using `FallbackLiteLlm` prevents single-provider downtime or rate-limit failures.
  - Using pre-chunked textbook RAG + `MAX_OUTPUT_TOKENS=700` keeps token usage low without needing expensive fine-tuning for factual recall.
