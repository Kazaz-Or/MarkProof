# MarkProof Project Rules

## Tech Stack & Quality
- Python 3.12+ | **uv** (Package management & Build)
- Core: `httpx`, `typer`, `pydantic` v2, `rich`
- Quality (DevDependencies): **ruff** (Linting & Formatting), `pytest`, `pyfakefs`

## Autonomy Protocol
- **Full Ownership:** You are responsible for creating files, implementing logic, and writing tests autonomously.
- **Git Restricted:** **DO NOT** execute `git add`, `git commit`, or `git push`. Leave all version control to the user.
- **Cycle:** Implement -> Test -> Lint -> Fix. Only report completion once the DOD is met.

## Definition of Done (DOD)
1. Feature is fully functional and matches the mission requirements.
2. Unit and integration tests in `tests/` cover the new logic.
3. `uv run pytest` passes 100%.
4. `uv run ruff check --fix .` and `uv run ruff format .` pass.

## Coding Standards
- Type hints required for all function signatures.
- Use `pathlib` for all filesystem interactions.
- Use `httpx.AsyncClient` for network-bound logic.
