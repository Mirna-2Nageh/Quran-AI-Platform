Quran AI Platform

An AI-powered Quran learning platform designed to help learners read, understand, memorize, and practice Quran recitation through intelligent, source-grounded assistance.

Project Status: In Development
Architecture: Modular Monolith with independently organized AI and Voice components.

Overview

Quran AI Platform aims to provide an integrated Quran learning experience by combining a Quran reader, verse-level tafsir, AI-assisted memorization, and a retrieval-augmented knowledge assistant.

The platform is designed with software engineering best practices in mind, including separation of concerns, clean code, automated testing, containerized development, and maintainable architecture.

Future iterations may introduce virtual Quran circles, teacher–student collaboration, and real-time voice sessions.

Core Features

1. Quran Reader & Tafsir

* Browse Quran chapters and verses.
* Select a verse to view its associated tafsir.
* Navigate between chapters and verses.
* Bookmark verses and track reading progress.
* Support Arabic text and right-to-left layouts.
* Maintain traceability to approved Quran and tafsir sources.

2. AI-Assisted Memorization

* Select a chapter or range of verses for memorization.
* Capture learner recitation through a microphone.
* Transcribe recitation using a speech recognition component.
* Compare the transcription against the target verses.
* Identify potential omissions, substitutions, and additional words.
* Display correction feedback and track memorization progress.

Scope note: Text-based comparison is not equivalent to a complete Tajweed assessment. Accurate evaluation of pronunciation, articulation, and recitation rules requires specialized audio analysis and appropriate validation.

3. Quran Knowledge Assistant

* Answer questions grounded in an approved Quran and tafsir knowledge base.
* Retrieve relevant passages before generating responses.
* Use Retrieval-Augmented Generation (RAG) to improve factual grounding.
* Organize AI workflows using LangGraph.
* Provide source references for generated answers.
* Handle unsupported questions without presenting unverified claims as facts.

4. User Accounts & Progress

* User registration and login.
* Secure authentication and protected endpoints.
* Personal bookmarks and reading history.
* Memorization progress tracking.
* User-specific learning data and preferences.

5. Quran Circles — Planned

* Create and manage Quran learning circles.
* Assign students to teachers and learning groups.
* Schedule sessions and track attendance.
* Monitor individual memorization progress.
* Support real-time audio sessions where required.

Technology Stack

Component	Technology
Frontend	React, TypeScript, Vite
Backend API	Python, FastAPI
AI workflows	LangGraph
Database	MongoDB, Beanie
Voice infrastructure	LiveKit, with a modular voice pipeline
Background processing	Celery, Redis
API documentation	OpenAPI, Swagger UI
Testing	pytest, frontend testing tools
Code quality	Ruff, Black, frontend linting and formatting
Containerization	Docker, Docker Compose
Continuous integration	GitHub Actions

The stack may evolve as implementation requirements and integration tests clarify the best approach.

Architecture

The project follows a modular architecture that separates user-facing APIs, business logic, data access, AI orchestration, and voice processing.

quran-ai-platform/
├── frontend/
├── backend/
├── ai_service/
├── voice_service/
├── infra/
├── docs/
├── tests/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md

Component Responsibilities

* frontend/ — User interface, feature components, API integration, and client-side state.
* backend/ — REST API, authentication integration, application services, domain logic, and persistence.
* ai_service/ — LangGraph workflows, retrieval, prompt management, LLM adapters, and AI evaluation.
* voice_service/ — Audio session management, speech processing, recitation assessment, and real-time voice integration.
* infra/ — Dockerfiles, local infrastructure configuration, and deployment-related resources.
* docs/ — Architecture decisions, development conventions, API contracts, and technical documentation.
* tests/ — Cross-component tests and shared evaluation scenarios.

The initial deployment may run these components in a single development environment using Docker Compose. Separate deployment and scaling can be introduced when justified by actual operational needs.

Engineering Principles

Clean Code

* Keep functions small and focused on a single responsibility.
* Use descriptive names and consistent conventions.
* Prefer explicit control flow over unnecessary abstractions.
* Keep business logic independent of framework-specific details where practical.
* Document important decisions rather than obvious implementation details.

Separation of Concerns

* API handlers must not contain complex business logic.
* Application services coordinate use cases.
* Repository interfaces isolate persistence concerns.
* Infrastructure adapters encapsulate external services.
* AI workflows remain separate from ordinary application logic.

Design Patterns

Apply design patterns when they solve a demonstrated problem:

* Repository Pattern: Isolate persistence operations behind clear interfaces.
* Dependency Injection: Supply service dependencies explicitly.
* Adapter Pattern: Standardize integrations with LLM, STT, and TTS providers.
* Strategy Pattern: Support interchangeable retrieval, transcription, or assessment strategies when needed.
* Factory Pattern: Centralize construction of complex dependencies where useful.

Patterns should improve maintainability and testability, not add unnecessary layers.

Testing & Code Quality

* Write unit tests for new business logic.
* Add integration tests for database and external-service boundaries.
* Test API validation, authentication, and authorization.
* Evaluate RAG retrieval quality and answer grounding.
* Test recitation comparison independently from speech recognition.
* Enforce linting and formatting through CI.

Configuration & Security

* Load configuration from environment variables.
* Validate required settings at application startup.
* Keep credentials and secrets out of source control.
* Use secure password hashing and appropriate token/session handling.
* Enforce user-level authorization on protected resources.
* Avoid logging passwords, tokens, or sensitive audio content.
* Pin and review dependencies as the project matures.

Prerequisites

* Docker Engine
* Docker Compose v2
* Git
* An internet connection for downloading dependencies and container images

Local Python and Node.js installations are not required when all development commands are executed inside the appropriate containers.

Getting Started

1. Clone the Repository

git clone <YOUR_REPOSITORY_URL>
cd quran-ai-platform

2. Configure Environment Variables

cp .env.example .env

Update the local configuration according to the documented variables.

Do not commit .env or any real credentials.

3. Build and Start the Services

docker compose up --build -d

4. Check Service Status

docker compose ps
docker compose logs -f

Verify that the required containers are running and healthy before using the application.

5. Access the Application

The following addresses are proposed development defaults. Actual ports will be defined in the Docker Compose configuration.

* Frontend: http://localhost:5173
* Backend API: http://localhost:8000
* Swagger UI: http://localhost:8000/docs
* ReDoc: http://localhost:8000/redoc

6. Stop the Services

docker compose down

To remove local Compose-managed volumes as well, use:

docker compose down -v

Warning: Removing volumes can permanently delete local database data. Use this command only when that is intended.

Development Workflow

Code Quality

Python code follows the repository’s Ruff and Black configuration.

ruff check .
black --check .
pytest

These commands should run in the backend development environment, with the required tools installed.

Apply formatting when necessary:

black .
ruff check . --fix

Automated fixes must be reviewed before committing.

Git Workflow

* Create focused feature branches.
* Keep commits small and descriptive.
* Open pull requests for review.
* Run relevant tests before merging.
* Avoid committing generated files, secrets, local databases, or temporary artifacts.

Example branch names:

feat/quran-reader
feat/tafsir-integration
feat/authentication
feat/recitation-feedback
feat/knowledge-assistant
test/rag-evaluation

Definition of Done

A change is ready to merge when:

* Its scope and acceptance criteria are satisfied.
* Relevant tests have been added and pass.
* Linting and formatting checks pass.
* API contracts and documentation are updated where necessary.
* Errors and edge cases are handled appropriately.
* No secrets or private data are introduced.
* The implementation follows the established architecture and conventions.

Data & Knowledge Base

The Quran reader, tafsir functionality, and AI assistant depend on trustworthy source material.

The data pipeline should preserve:

* Source identity and licensing information.
* Chapter and verse identifiers.
* Tafsir attribution and edition metadata.
* Document provenance and ingestion timestamps.
* Stable references from generated answers to retrieved passages.

Quran text must be obtained from an appropriate authoritative source. Generative models must not be treated as the source of truth for Quranic text or tafsir.

The knowledge ingestion and indexing process should be reproducible and independently testable.

AI & Voice Design

Retrieval-Augmented Generation

The AI assistant follows a retrieval-first approach:

1. Receive and validate a question.
2. Retrieve relevant passages from the approved knowledge base.
3. Evaluate retrieval results and source relevance.
4. Generate an answer grounded in the retrieved context.
5. Return the answer with available source references.

LangGraph is used to organize the workflow, control transitions, and support error handling and evaluation.

Voice Processing

The voice pipeline is designed around replaceable components:

1. Capture audio.
2. Process incoming audio.
3. Transcribe speech using an STT component.
4. Compare recognized words with the target Quranic verses.
5. Produce structured feedback.
6. Return results to the user.

LiveKit can provide real-time audio session infrastructure. Speech recognition and speech synthesis are separate integrations and must be configured independently.

The architecture should not assume that transcription alone can reliably assess Tajweed or all pronunciation errors.

Roadmap

Phase 1 — Project Foundation

* Repository structure and development conventions.
* Docker Compose environment.
* FastAPI application and MongoDB integration.
* Configuration, logging, and error handling.
* CI checks and initial tests.

Phase 2 — Core Application

* Authentication and protected routes.
* Quran reader and tafsir integration.
* User bookmarks and reading progress.
* Initial frontend-to-backend integration.

Phase 3 — AI Knowledge Assistant

* Knowledge ingestion pipeline.
* Retrieval and indexing.
* LangGraph orchestration.
* Source-grounded answers.
* Retrieval and answer-quality evaluation.

Phase 4 — Memorization & Voice

* Audio capture and transcription.
* Verse alignment and text comparison.
* Structured correction feedback.
* Voice pipeline evaluation.
* LiveKit integration where needed.

Phase 5 — Quran Circles

* Teacher and student roles.
* Circle and membership management.
* Scheduling and attendance.
* Progress reports.
* Real-time learning sessions.

Contributing

Contributions should follow the established coding conventions and architecture.

Before submitting a pull request:

1. Describe the problem and proposed change.
2. Add or update tests.
3. Run formatting, linting, and relevant tests.
4. Update documentation when behavior or configuration changes.
5. Confirm that the change does not introduce unnecessary dependencies or abstractions.

License

The project’s license and distribution terms will be defined before public release. Third-party datasets, Quran text, tafsir content, and model assets remain subject to their respective licenses and usage conditions.

⸻

Disclaimer: This platform is an educational tool. AI-generated explanations and recitation feedback should not replace qualified scholarly guidance or a qualified Quran teacher.
