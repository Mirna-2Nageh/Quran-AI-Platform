# Quran AI Platform

An AI-powered Quran learning platform designed to help learners read, understand, memorize, and practice Quran recitation through intelligent, source-grounded assistance.

**Project Status:** In Development
**Architecture:** Modular Monolith with independently organized AI and Voice components.

## Current Implementation

See [Current Implementation](docs/current-implementation.md) for the implemented features, local setup, ASR model, and tests.

## Overview

Quran AI Platform aims to provide an integrated Quran learning experience by combining a Quran reader, verse-level tafsir, AI-assisted memorization, and a retrieval-augmented knowledge assistant.

The platform is being developed with software engineering best practices in mind, including separation of concerns, clean code, automated testing, maintainable architecture, and reproducible development workflows.

Future iterations may introduce virtual Quran circles, teacher–student collaboration, and real-time voice sessions.

> **Current implementation:** The repository includes an initial FastAPI backend, a health endpoint, centralized application settings using Pydantic Settings, Python dependency configuration, and automated tests. The frontend, database integration, AI workflows, voice services, and containerized environment remain planned work.

## Core Features

### 1. Quran Reader & Tafsir

Planned capabilities:

- Browse Quran chapters and verses.
- Select a verse to view its associated tafsir.
- Navigate between chapters and verses.
- Bookmark verses and track reading progress.
- Support Arabic text and right-to-left layouts.
- Maintain traceability to approved Quran and tafsir sources.

### 2. AI-Assisted Memorization

Planned capabilities:

- Select a chapter or range of verses for memorization.
- Capture learner recitation through a microphone.
- Transcribe recitation using a speech recognition component.
- Compare the transcription against the target verses.
- Identify potential omissions, substitutions, and additional words.
- Display correction feedback and track memorization progress.

**Scope note:** Text-based comparison is not equivalent to a complete Tajweed assessment. Accurate evaluation of pronunciation, articulation, and recitation rules requires specialized audio analysis and appropriate validation.

### 3. Quran Knowledge Assistant

Planned capabilities:

- Answer questions grounded in an approved Quran and tafsir knowledge base.
- Retrieve relevant passages before generating responses.
- Use Retrieval-Augmented Generation (RAG) to improve factual grounding.
- Organize AI workflows using LangGraph.
- Provide source references for generated answers.
- Handle unsupported questions without presenting unverified claims as facts.

### 4. User Accounts & Progress

Planned capabilities:

- User registration and login.
- Secure authentication and protected endpoints.
- Personal bookmarks and reading history.
- Memorization progress tracking.
- User-specific learning data and preferences.

### 5. Quran Circles — Planned

- Create and manage Quran learning circles.
- Assign students to teachers and learning groups.
- Schedule sessions and track attendance.
- Monitor individual memorization progress.
- Support real-time audio sessions where required.

## Technology Stack

The following is the intended technology stack. Not every component has been integrated into the current implementation.

| Component | Technology | Status |
|---|---|---|
| Frontend | React, TypeScript, Vite | Planned |
| Backend API | Python, FastAPI | Initial implementation |
| Application configuration | Pydantic Settings | Implemented |
| AI workflows | LangGraph | Planned |
| Database | MongoDB, Beanie | Planned |
| Voice infrastructure | LiveKit, modular voice pipeline | Planned |
| Background processing | Celery, Redis | Planned |
| API documentation | OpenAPI, Swagger UI | Available through FastAPI |
| Testing | pytest | Initial tests implemented |
| Code quality | Ruff, Black | Configured |
| Containerization | Docker, Docker Compose | Planned |
| Continuous integration | GitHub Actions | Planned |

The stack may evolve as implementation requirements and integration tests clarify the best approach.

## Architecture

The project follows a modular architecture that separates user-facing APIs, business logic, data access, AI orchestration, and voice processing.

The intended repository structure is:

```text
Quran-AI-Platform/
├── frontend/                  # Planned
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   └── config.py          # Application settings
│   └── tests/
│       ├── test_main.py       # Health endpoint tests
│       └── test_config.py     # Configuration tests
├── ai_service/                # Planned
├── voice_service/             # Planned
├── infra/                     # Planned
├── docs/
├── tests/                     # Planned cross-component tests
├── .github/
│   └── workflows/             # CI workflow planned
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

This is a conceptual overview of the repository. Directories marked as planned may not exist yet.

### Component Responsibilities

- `frontend/` — User interface, feature components, API integration, and client-side state.
- `backend/` — REST API, application services, domain logic, authentication integration, and persistence.
- `ai_service/` — LangGraph workflows, retrieval, prompt management, LLM adapters, and AI evaluation.
- `voice_service/` — Audio session management, speech processing, recitation assessment, and real-time voice integration.
- `infra/` — Dockerfiles, local infrastructure configuration, and deployment-related resources.
- `docs/` — Architecture decisions, development conventions, API contracts, and technical documentation.
- `tests/` — Cross-component tests and shared evaluation scenarios.

The initial deployment may run these components in a single development environment using Docker Compose. Separate deployment and scaling can be introduced when justified by actual operational needs.

## Engineering Principles

### Clean Code

- Keep functions small and focused on a single responsibility.
- Use descriptive names and consistent conventions.
- Prefer explicit control flow over unnecessary abstractions.
- Keep business logic independent of framework-specific details where practical.
- Document important decisions rather than obvious implementation details.

### Separation of Concerns

- API handlers should not contain complex business logic.
- Application services coordinate use cases.
- Repository interfaces isolate persistence concerns when needed.
- Infrastructure adapters encapsulate external services.
- AI workflows remain separate from ordinary application logic.

### Design Patterns

Apply design patterns when they solve a demonstrated problem:

- **Repository Pattern:** Isolate persistence operations behind clear interfaces.
- **Dependency Injection:** Supply service dependencies explicitly.
- **Adapter Pattern:** Standardize integrations with LLM, STT, and TTS providers.
- **Strategy Pattern:** Support interchangeable retrieval, transcription, or assessment strategies when needed.
- **Factory Pattern:** Centralize construction of complex dependencies where useful.

Patterns should improve maintainability and testability, not add unnecessary layers.

## Testing & Code Quality

- Write unit tests for new business logic.
- Add integration tests for database and external-service boundaries.
- Test API validation, authentication, and authorization as these features are introduced.
- Evaluate RAG retrieval quality and answer grounding when the AI assistant is implemented.
- Test recitation comparison independently from speech recognition.
- Enforce linting and formatting through CI when the CI workflow is introduced.

### Current Python Quality Checks

The repository uses Ruff and Black for Python code quality and pytest for automated tests.

Run the following commands from the repository root with the project virtual environment activated:

```bash
python -m ruff check .
python -m black --check backend/app backend/tests
python -m pytest -v
```

To apply formatting or automatic lint fixes:

```bash
python -m black backend/app backend/tests
python -m ruff check . --fix
```

Review automatic fixes before committing.

## Configuration & Security

Application settings are centralized in `backend/app/config.py` using Pydantic Settings.

- Environment variables use the `QURAN_AI_` prefix.
- Available settings are `app_name`, `app_version`, `environment`, and `debug`.
- Default values allow the API to start without a local `.env` file or secrets.
- `.env.example` documents the supported local configuration.
- A local `.env` file can override default settings and must not be committed.
- Never store credentials, API keys, or other secrets in `.env.example`.
- The `environment` setting is currently configuration-only; environment-specific behavior has not been implemented.
- Authentication, authorization, secure password handling, and sensitive-data logging safeguards remain future work.
- Dependency constraints should be reviewed and maintained as the project matures.

## Prerequisites

- Python 3.10 or later, below Python 3.14.
- Git.
- Internet access to install Python dependencies.

Docker and Docker Compose are not required for the current backend-only setup.

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Mirna-2Nageh/Quran-AI-Platform.git
cd Quran-AI-Platform
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

If the virtual environment already exists, activate it rather than creating it again.

### 3. Install the Project and Development Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The editable installation installs the project and its declared development dependencies, including FastAPI, Uvicorn, Pydantic Settings, pytest, Ruff, Black, and HTTPX.

### 4. Configure Environment Variables (Optional)

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` to override the defaults if needed.

| Variable | Default | Purpose |
|---|---|---|
| `QURAN_AI_APP_NAME` | `Quran AI Platform API` | FastAPI application title |
| `QURAN_AI_APP_VERSION` | `0.1.0` | API version |
| `QURAN_AI_ENVIRONMENT` | `development` | Environment label: `development`, `testing`, or `production` |
| `QURAN_AI_DEBUG` | `false` | FastAPI debug mode |

This step is optional. Do not commit your local `.env` file.

### 5. Start the Backend API

From the repository root:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

The default port is `8000`. If it is already occupied, choose an available port:

```bash
python -m uvicorn app.main:app --app-dir backend --reload --port 8003
```

### 6. Verify the API

With the server running, open the following addresses. Replace port `8000` if you selected a different port.

- **Health check:** http://127.0.0.1:8000/health
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

The health endpoint should return:

```json
{
  "status": "ok"
}
```

### 7. Stop the Development Server

Press `Ctrl+C` in the terminal running Uvicorn.

Docker Compose commands and frontend instructions will be added when the corresponding configuration and components are implemented.

## Development Workflow

### Code Quality

Before committing Python changes, run:

```bash
python -m ruff check .
python -m black --check backend/app backend/tests
python -m pytest -v
git diff --check
```

Apply formatting when necessary and review all resulting changes.

### Git Workflow

- Create focused feature branches.
- Keep commits small and descriptive.
- Open pull requests for review.
- Run relevant tests before merging.
- Avoid committing generated files, secrets, local databases, or temporary artifacts.

Example branch names:

```text
feat/quran-reader
feat/tafsir-integration
feat/authentication
feat/recitation-feedback
feat/knowledge-assistant
test/rag-evaluation
```

## Definition of Done

A change is ready to merge when:

- Its scope and acceptance criteria are satisfied.
- Relevant tests have been added and pass.
- Linting and formatting checks pass.
- API contracts and documentation are updated where necessary.
- Errors and edge cases are handled appropriately.
- No secrets or private data are introduced.
- The implementation follows established architecture and conventions.

## Data & Knowledge Base

The Quran reader, tafsir functionality, and AI assistant depend on trustworthy source material.

The data pipeline should preserve:

- Source identity and licensing information.
- Chapter and verse identifiers.
- Tafsir attribution and edition metadata.
- Document provenance and ingestion timestamps.
- Stable references from generated answers to retrieved passages.

Quran text must be obtained from an appropriate authoritative source. Generative models must not be treated as the source of truth for Quranic text or tafsir.

The knowledge ingestion and indexing process should be reproducible and independently testable.

## AI & Voice Design

### Retrieval-Augmented Generation

The planned AI assistant follows a retrieval-first approach:

1. Receive and validate a question.
2. Retrieve relevant passages from the approved knowledge base.
3. Evaluate retrieval results and source relevance.
4. Generate an answer grounded in the retrieved context.
5. Return the answer with available source references.

LangGraph is intended to organize the workflow, control transitions, and support error handling and evaluation.

### Voice Processing

The planned voice pipeline is designed around replaceable components:

1. Capture audio.
2. Process incoming audio.
3. Transcribe speech using an STT component.
4. Compare recognized words with the target Quranic verses.
5. Produce structured feedback.
6. Return results to the user.

LiveKit can provide real-time audio session infrastructure. Speech recognition and speech synthesis are separate integrations and must be configured independently.

The architecture should not assume that transcription alone can reliably assess Tajweed or all pronunciation errors.

## Roadmap

### Phase 1 — Project Foundation

- [x] Repository development conventions.
- [x] Initial FastAPI application and health endpoint.
- [x] Python project and development dependency configuration.
- [x] Initial health endpoint test.
- [x] Centralized application settings with Pydantic Settings.
- [x] Environment variable configuration example.
- [ ] Structured logging and error handling.
- [ ] Docker Compose environment.
- [ ] MongoDB integration.
- [ ] CI checks and expanded tests.

### Phase 2 — Core Application

- [ ] Authentication and protected routes.
- [ ] Quran reader and tafsir integration.
- [ ] User bookmarks and reading progress.
- [ ] Initial frontend-to-backend integration.

### Phase 3 — AI Knowledge Assistant

- [ ] Knowledge ingestion pipeline.
- [ ] Retrieval and indexing.
- [ ] LangGraph orchestration.
- [ ] Source-grounded answers.
- [ ] Retrieval and answer-quality evaluation.

### Phase 4 — Memorization & Voice

- [ ] Audio capture and transcription.
- [ ] Verse alignment and text comparison.
- [ ] Structured correction feedback.
- [ ] Voice pipeline evaluation.
- [ ] LiveKit integration where needed.

### Phase 5 — Quran Circles

- [ ] Teacher and student roles.
- [ ] Circle and membership management.
- [ ] Scheduling and attendance.
- [ ] Progress reports.
- [ ] Real-time learning sessions.

## Contributing

Contributions should follow the established coding conventions and architecture.

Before submitting a pull request:

1. Describe the problem and proposed change.
2. Add or update tests.
3. Run formatting, linting, and relevant tests.
4. Update documentation when behavior or configuration changes.
5. Confirm that the change does not introduce unnecessary dependencies or abstractions.

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details. Third-party datasets, Quran text, tafsir content, and model assets remain subject to their respective licenses and usage conditions.

---

**Disclaimer:** This platform is an educational tool. AI-generated explanations and recitation feedback should not replace qualified scholarly guidance or a qualified Quran teacher.
