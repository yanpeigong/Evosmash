# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Vite + React frontend (`components/`, `pages/`, `context/`, `utils/`, `styles/`).
- `backend/` contains the FastAPI service and analysis pipeline:
  - `core/` for vision, physics, memory, agent, and shared utilities.
  - `services/` for orchestration/business logic.
  - `schemas/` for response/data contracts.
  - `tests/` for backend test coverage.
- `assets/` and `public/` store static media and UI assets.
- `android/` is the Capacitor Android project.
- Put model checkpoints in `backend/checkpoints/` locally (do not commit large weights by default).

## Build, Test, and Development Commands
- `npm install` — install frontend dependencies.
- `npm run dev` — run frontend locally (Vite default: `http://localhost:5173`).
- `npm run build` — create production frontend build in `dist/`.
- `npm run lint` — run ESLint for `js/jsx`.
- `cd backend && pip install -r requirements.txt` — install backend dependencies.
- `cd backend && python main.py` — start FastAPI backend (default port `8000`).
- `pytest` — run backend tests defined in `pytest.ini`.

## Coding Style & Naming Conventions
- Frontend: 2-space indentation, semicolons, functional React components.
- Use `PascalCase` for component files (e.g., `PageTransition.jsx`), `camelCase` for utility modules, and descriptive CSS filenames under `src/styles/`.
- Backend Python: follow PEP 8 with 4-space indentation, `snake_case` for functions/modules, and clear typed interfaces where practical.
- Run `npm run lint` before submitting changes.

## Testing Guidelines
- Testing stack: `pytest` + FastAPI `TestClient`.
- Test location/patterns are enforced by `pytest.ini`: `backend/tests`, file pattern `test_*.py`.
- Add or update tests when changing endpoints, validation, response schema, or service logic.
- Keep tests deterministic by mocking external services/models when needed.

## Commit & Pull Request Guidelines
- Recent history includes very short messages (`update`, `debug`); prefer clearer format: `<scope>: <imperative summary>` (example: `backend: validate upload extension`).
- Keep commits focused and avoid mixing unrelated frontend/backend refactors.
- PRs should include:
  - Goal and user-visible impact.
  - Key files changed.
  - Verification steps (`npm run lint`, `pytest`, manual API/UI checks).
  - Screenshots/GIFs for UI changes.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and keep secrets out of version control.
- Do not commit API keys, model checkpoints, or large video artifacts unless explicitly required.
- If changing runtime limits/CORS, keep `backend/config.py` and related docs in sync.
