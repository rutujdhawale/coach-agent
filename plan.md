# Implementation Plan: Examblue Performance Coach Agent (Backend)

## 1. Goal
Initialize a backend-only FastAPI project for the "Examblue Performance Coach" agent using Google ADK and LiteLLM (Groq primary, Gemini fallback).

## 2. Phase 1: Setup & Environment
- [ ] Initialize Python environment and `requirements.txt`.
- [ ] Create base directory structure as per `prompt.md`.
- [ ] Setup `.env` configuration template.
- [ ] Initialize `main.py` with FastAPI app instance.

## 3. Phase 2: Foundation & Data
- [ ] Define MongoDB repository layer.
- [ ] Configure environment variables/config loading.
- [ ] Implement health check and core API scaffold (`/api/v1`).

## 4. Phase 3: Agent Orchestration (Google ADK)
- [ ] Define Agent logic in `app/agents/performance_coach/`.
- [ ] Configure LiteLLM router (Groq/Gemini logic).
- [ ] Implement core tools: `exam_history`, `weak_topics`, `recommendations`.

## 5. Phase 4: Integration & Testing
- [ ] Implement REST endpoints.
- [ ] Write initial unit/integration tests.
- [ ] Prepare Dockerfile and deployment docs.

---
**Senior Engineer Note:** We will enforce clean architecture (Repository Pattern) to ensure the agent logic remains decoupled from the data layer and LLM provider interfaces.
