# ==============================================================================
# AQG Studio - Development Makefile
# ==============================================================================

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend test test-backend test-frontend lint lint-backend lint-frontend typecheck typecheck-backend typecheck-frontend format build clean verify

help:
	@echo "AQG Studio Makefile targets:"
	@echo "  install            Install all dependencies (frontend and backend)"
	@echo "  dev                Run backend and frontend concurrently"
	@echo "  dev-backend        Run FastAPI backend (uvicorn)"
	@echo "  dev-frontend       Run Next.js frontend"
	@echo "  test               Run backend (pytest) and frontend (jest/vitest) tests"
	@echo "  lint               Run linting across backend (ruff) and frontend (eslint)"
	@echo "  typecheck          Run type checking across backend (mypy) and frontend (tsc)"
	@echo "  format             Format codebase with ruff and prettier"
	@echo "  build              Build frontend and backend packages"
	@echo "  clean              Remove temporary files, caches, and build artifacts"
	@echo "  verify             Execute complete lint, typecheck, test, and build suite"

install: install-backend install-frontend

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev:
	@echo "Starting development environment..."
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals or use a task runner."

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

dev-frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && pytest --verbose tests/

test-frontend:
	cd frontend && npm test -- --passWithNoTests

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check .

lint-frontend:
	cd frontend && npm run lint

typecheck: typecheck-backend typecheck-frontend

typecheck-backend:
	cd backend && mypy app

typecheck-frontend:
	cd frontend && npm run typecheck

format:
	cd backend && ruff format .
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css,json}"

build:
	cd frontend && npm run build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf frontend/.next frontend/out backend/dist

verify: lint typecheck test
	@echo "=============================================="
	@echo " All verification quality gates passed! "
	@echo "=============================================="
