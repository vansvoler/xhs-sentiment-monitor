# Repository Guidelines

## Project Structure & Module Organization
The backend is a Python 3.11 FastAPI service. Entry point is `main.py`, which wires routes, MongoDB startup, the scheduler, and the WebSocket heartbeat. Application code lives under `src/`:

- `src/api/`: HTTP route modules such as `notes.py`, `comments.py`, and `config.py`
- `src/collectors/`: XiaoHongShu/TikHub ingestion and scheduled collection jobs
- `src/analyzers/`: sentiment providers and classification logic
- `src/services/`: higher-level trend and competitor analysis
- `src/db/`: MongoDB client and initialization
- `src/models/`: Pydantic models
- `src/websocket/`: real-time push management

Shell helpers live in `scripts/`. Add tests under a top-level `tests/` package mirroring `src/` paths, for example `tests/api/test_notes.py`.

## Build, Test, and Development Commands
Use `uv` for environment management because `uv.lock` is committed.

- `uv sync --dev`: install runtime and dev dependencies into `.venv`
- `uv run python main.py`: start the API locally on `HOST`/`PORT`
- `bash scripts/dev.sh`: run the development server using the local virtualenv
- `bash scripts/start.sh`: launch the service in the background and write logs to `logs/server.log`
- `bash scripts/stop.sh`: stop background `python main.py` processes
- `uv run pytest`: run the test suite
- `uv run ruff check . && uv run black --check . && uv run mypy src`: lint, format-check, and type-check

## Coding Style & Naming Conventions
Follow Black and Ruff settings from `pyproject.toml`: 4-space indentation and 88-character lines. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and descriptive route module names under `src/api/`. Prefer explicit type hints on public functions and async database/service boundaries.

## Testing Guidelines
Use `pytest` with `pytest-asyncio` for async code. Name files `test_*.py` and keep test names behavior-focused, such as `test_health_returns_ok`. Cover API handlers, scheduler logic, and analyzer edge cases. For database-dependent tests, isolate test data and avoid using the production MongoDB database name.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit prefixes, including `feat:`, `fix:`, and `chore:`. Keep subjects short and imperative. PRs should include a concise summary, affected modules, config changes, and test evidence (`uv run pytest`, lint output, or manual API checks). Link issues when applicable and include screenshots only for API docs or UI-facing changes.

## Security & Configuration Tips
Configuration is loaded from `.env` via `src/config.py`. Never commit secrets such as `TIKHUB_TOKEN` or `SENTIMENT_API_KEY`. Local development also expects MongoDB, and some workflows may depend on Redis; document any new environment variables in the PR that introduces them.
