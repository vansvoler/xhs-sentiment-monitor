# Repository Guidelines

## Project Structure & Module Organization
This project monitors XiaoHongShu note and comment sentiment. The core flow is TikHub API -> collectors -> MongoDB -> sentiment analysis -> WebSocket broadcast. Backend code lives in `backend/src/`: `collectors/` handles TikHub ingestion and APScheduler jobs, `api/` exposes `/api/notes`, `/comments`, `/sentiment`, `/trends`, and `/competitors`, `analyzers/` runs Senta or fallback rules, and `websocket/` pushes `new_note`, `sentiment_update`, `alert`, and `heartbeat` events. The Next.js frontend lives in `frontend/src/` with routes in `app/`, shared code in `lib/`, and dashboard/chart components in `components/`. Planning docs live in `docs/`.

## Build, Test, and Development Commands
- `cd backend && uv venv --python 3.11 && uv pip install -e ".[dev]"`: first-time backend setup.
- `cd backend && bash scripts/dev.sh`: start the backend through the local virtualenv helper.
- `cd backend && uv run python -m src.collectors.xhs_api 口红`: run one collector smoke test without the scheduler.
- `cd frontend && npm install`: install frontend dependencies.
- `cd frontend && npm run dev`: start the Next.js app.
- `cd frontend && npm run build`: create a production build.
- `cd frontend && npm run lint`: run ESLint.

## Coding Style & Naming Conventions
Python follows Black/Ruff defaults configured in `backend/pyproject.toml`: 4-space indentation, 88-column lines, `snake_case` for modules/functions, `PascalCase` for classes. TypeScript uses the repo ESLint config in `frontend/eslint.config.mjs`; prefer `PascalCase` React components, `camelCase` helpers, and colocated files like `trend-line.tsx` or `api.ts`. Keep modules focused and avoid mixing API, data, and presentation logic.

## Testing Guidelines
Backend dev dependencies include `pytest`, `pytest-asyncio`, `ruff`, `black`, and `mypy`. Run `cd backend && uv run pytest` for tests and `cd backend && uv run ruff check . && uv run black --check . && uv run mypy src` before opening a PR. Frontend test scripts are not set up yet; at minimum, run `npm run lint` and document manual checks for dashboard flows.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit prefixes such as `feat:`, `fix:`, and `chore:`. Keep subjects short and imperative. PRs should include a concise summary, touched areas (`backend/src/api`, `frontend/src/components`, etc.), any env or schema changes, and evidence of validation. Add screenshots for UI changes.

## Configuration & Contributor Notes
Never commit secrets in `.env` files or API tokens. Copy `backend/.env.example` to `backend/.env` and set `TIKHUB_TOKEN`, `MONGODB_URL`, `MONITOR_KEYWORDS`, `COMPETITORS`, and `TIKHUB_PROVIDER_PRIORITY`; frontend uses `frontend/.env.local` for `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`. TikHub calls are billable, so avoid unnecessary restarts during development, and do not raise per-page fetch limits above 20. When working inside `backend/` or `frontend/`, check the local `AGENTS.md` or `CLAUDE.md` there for app-specific rules before making deeper changes.
