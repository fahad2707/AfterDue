.PHONY: setup backend frontend test lint check clean

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

test:
	cd backend && $(UV) run pytest -q

lint:
	cd backend && $(UV) run ruff check .
	cd frontend && npx tsc --noEmit

check: lint test

clean:
	rm -rf backend/.venv frontend/.next frontend/node_modules
