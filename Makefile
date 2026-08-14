.PHONY: help dev test build up down demo clean lint format install migrate

PYTHON := python
PIP := pip
NPM := npm
DOCKER := docker
DC := docker compose

help:
	@echo "Agentic AI VAPT Framework — Available Commands"
	@echo "================================================"
	@echo ""
	@echo "Development:"
	@echo "  make install       Install all dependencies (backend + frontend)"
	@echo "  make dev           Start backend + frontend in dev mode"
	@echo "  make dev-backend   Start backend only (SQLite, hot reload)"
	@echo "  make dev-frontend  Start frontend only"
	@echo ""
	@echo "Database:"
	@echo "  make migrate       Run Alembic migrations"
	@echo "  make migrate-new   Create new migration (MSG=description)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-int      Run integration tests"
	@echo "  make test-e2e      Run end-to-end tests"
	@echo "  make test-cov      Run tests with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  make up            Start full stack (Docker Compose)"
	@echo "  make up-no-ollama  Start without Ollama (if running externally)"
	@echo "  make down          Stop all services"
	@echo "  make build         Build Docker images"
	@echo ""
	@echo "Demo:"
	@echo "  make demo          Run full demo scenario (requires running backend)"
	@echo "  make demo-quick    Quick smoke test"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linting (ruff + mypy)"
	@echo "  make format        Format code (ruff format + black)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove build artifacts, caches"

install:
	@echo "Installing backend dependencies..."
	cd backend && $(PIP) install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && $(NPM) install
	@echo "Installation complete."

dev-backend:
	@echo "Starting backend (dev mode, SQLite)..."
	cd backend && USE_SQLITE=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "Starting frontend (dev mode)..."
	cd frontend && $(NPM) run dev

dev:
	@echo "Starting dev stack..."
	@start cmd /k "cd backend && USE_SQLITE=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
	@start cmd /k "cd frontend && npm run dev"
	@echo "Backend: http://localhost:8000/docs"
	@echo "Frontend: http://localhost:5173"

migrate:
	@echo "Running Alembic migrations..."
	cd backend && alembic upgrade head

migrate-new:
	@echo "Creating migration: $(MSG)"
	cd backend && alembic revision --autogenerate -m "$(MSG)"

test:
	@echo "Running all tests..."
	cd backend && pytest tests/ -v --tb=short

test-unit:
	cd backend && pytest tests/unit/ -v --tb=short

test-int:
	cd backend && pytest tests/integration/ -v --tb=short

test-e2e:
	cd backend && pytest tests/e2e/ -v --tb=short

test-cov:
	cd backend && pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

lint:
	cd backend && ruff check app/ tests/
	cd backend && mypy app/ --ignore-missing-imports

format:
	cd backend && ruff format app/ tests/

up:
	$(DC) up --build -d
	@echo "Services started. Dashboard: http://localhost:5173"

up-no-ollama:
	$(DC) up --build -d backend frontend postgres sandbox
	@echo "Services started (without Ollama). Dashboard: http://localhost:5173"

down:
	$(DC) down

build:
	$(DC) build

demo:
	@echo "Running VAPT demo scenario..."
	cd backend && $(PYTHON) -m app.cli demo

demo-quick:
	@echo "Running quick smoke test..."
	cd backend && $(PYTHON) -m app.cli demo --quick

clean:
	@echo "Cleaning build artifacts..."
	rd /s /q backend\__pycache__ 2>NUL || true
	rd /s /q backend\.pytest_cache 2>NUL || true
	rd /s /q backend\htmlcov 2>NUL || true
	rd /s /q backend\vapt.db 2>NUL || true
	del /f backend\*.db 2>NUL || true
	rd /s /q frontend\node_modules\.cache 2>NUL || true
	rd /s /q frontend\dist 2>NUL || true
	@echo "Clean complete."
