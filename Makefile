.PHONY: setup backend frontend test test-unit test-integration lint check clean demo demo-reset

UV := $(HOME)/.local/bin/uv

setup:
	@test -f .env || cp .env.example .env
	@test -f frontend/.env.local || cp frontend/.env.local.example frontend/.env.local
	cd backend && $(UV) sync --group dev
	cd frontend && npm install
	@echo "Setup complete. Add MONGODB_URI to .env, then: make backend / make frontend"

backend:
	cd backend && $(UV) run uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# Both suites in one process on purpose: running them separately hid INC-005.
test:
	cd backend && $(UV) run pytest -q

# No database required.
test-unit:
	cd backend && $(UV) run pytest tests/unit -q

# Needs MONGODB_URI in .env. Uses a throwaway database, never `reclaim`.
test-integration:
	cd backend && $(UV) run pytest tests/integration -q

lint:
	cd backend && $(UV) run ruff check .
	cd frontend && npx tsc --noEmit

check: lint test

clean:
	rm -rf backend/.venv frontend/.next frontend/node_modules

# Requires `make backend` in another terminal. Canonical: 100 / seed 42 / budget 25.
demo:
	bash scripts/demo.sh

demo-reset:
	bash scripts/demo.sh reset
