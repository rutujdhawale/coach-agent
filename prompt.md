# Updated Architecture: Backend-Only MVP

Remove the frontend completely from the current project scope.

Do not build React, JavaScript, Vite, Next.js, HTML pages or any frontend components.

## 1. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Agent Framework | Google Agent Development Kit (ADK) |
| Database | MongoDB Atlas |
| Primary LLM | Groq API (free tier) |
| Fallback LLM | Gemini API (free quota) |
| LLM Integration | LiteLLM |
| Cloud | Google Cloud Platform |
| Deployment | Google Cloud Run |
| File Storage | Google Cloud Storage |
| Secrets | Google Secret Manager |
| API Testing | Postman + Pytest |

## 2. Project Structure

examblue-performance-coach/

    backend/
        app/
            main.py
            api/
                routes/
                dependencies.py
            agents/
                performance_coach/
                    agent.py
                    prompts.py
                    tools.py
            services/
                performance_analyzer.py
                recommendation_engine.py
                question_service.py
                llm_router.py
            providers/
                base.py
                groq_provider.py
                gemini_provider.py
            repositories/
                base.py
                mongodb_repository.py
            models/
            security/
            config/
        tests/
        requirements.txt
        Dockerfile

    infrastructure/
        cloud-run/
        cloud-storage/
        cloud-build/

    data/
        demo/

    docs/
        architecture.md
        api-documentation.md
        integration.md
        deployment.md
        security.md

    .env.example
    README.md

## 3. Backend Development Priorities

Build the following in order:

1. FastAPI application and configuration.
2. MongoDB Atlas connection and repository layer.
3. Authentication and student data isolation.
4. Deterministic student performance analysis.
5. Google ADK Performance Coach agent.
6. Groq primary LLM integration.
7. Gemini fallback integration.
8. Agent tools for retrieving exam history, identifying weak topics, explaining incorrect answers and generating recommendations.
9. REST API endpoints for all functionality.
10. Unit tests, integration tests and API documentation.
11. Docker configuration and Google Cloud deployment.

## 4. API-First Development

Expose functionality through documented REST APIs.

Include endpoints for:
- Health checks.
- Student profiles.
- Exam history.
- Performance analysis.
- Weak-topic identification.
- Personalized recommendations.
- Practice question retrieval.
- Answer evaluation.
- Agent conversations.
- Student progress.

Use FastAPI's Swagger UI for interactive API testing.

## 5. Future Frontend Compatibility

Although no frontend is required now:

- Keep APIs independent of the agent implementation.
- Use consistent JSON request and response schemas.
- Add CORS configuration for future frontend origins.
- Keep authentication compatible with future web and mobile clients.
- Version APIs using `/api/v1/`.
- Avoid returning internal database documents directly.

## 6. Development Rules

- Backend-only implementation.
- No frontend code or UI work.
- No unnecessary microservices.
- No Kubernetes for the initial MVP.
- Use MongoDB as the only primary database.
- Use Groq first and Gemini as fallback.
- Use Google ADK for agent orchestration.
- Keep calculations deterministic and testable.
- Use real database operations, not fabricated responses.
- Test APIs through Pytest and Postman.
- Keep deployment costs minimal.

Start by inspecting the existing repository, documenting the revised architecture and preparing an implementation plan. Do not modify unrelated existing functionality.