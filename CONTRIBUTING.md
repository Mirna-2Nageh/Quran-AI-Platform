# Contributing Guide

## Development Principles

- Keep changes focused and easy to review.
- Prefer simple, explicit solutions over premature abstractions.
- Keep API handlers thin and business logic independently testable.
- Add tests for new functionality and relevant bug fixes.
- Never commit secrets, credentials, private user data, or local environment files.
- Update documentation when an architectural decision or public contract changes.

## Branching

Create a dedicated branch for each change.

Examples:

- `feat/quran-reader`
- `feat/knowledge-assistant`
- `fix/recitation-comparison`
- `test/rag-evaluation`
- `docs/architecture`
- `chore/repository-conventions`

Avoid committing directly to `main`.

## Commit Messages

Use clear, imperative, scoped commit messages.

Examples:

- `chore: add repository conventions`
- `docs: document system architecture`
- `feat: add Quran reader API`
- `test: cover verse retrieval`
- `fix: validate bookmark ownership`

Each commit should represent one logical change.

## Quality Checks

Run the relevant checks before opening a pull request.

Python checks, once the backend tooling is configured:

    ruff check .
    black --check .
    pytest

Frontend checks should use the scripts configured in the frontend package.

Do not claim a check passed unless it was actually executed successfully.

## Pull Requests

A pull request should describe:

- What changed and why.
- Relevant implementation or architectural decisions.
- Tests and quality checks performed.
- Known limitations or follow-up work.

Keep the change focused and update relevant documentation when necessary.
