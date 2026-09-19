# RAILOPTIX — Project Makefile
# ─────────────────────────────────────────────────────────────────────────────
# Prerequisites: Python 3.10+ (.venv at project root), Node.js 18+
# Activate venv first: source .venv/bin/activate
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help backend frontend test lint build demo install install-frontend

# Default target
help:
	@echo ""
	@echo "  RAILOPTIX — Available Commands"
	@echo "  ─────────────────────────────────────────────────────────────────"
	@echo "  make backend          Start FastAPI backend (uvicorn, port 8000)"
	@echo "  make frontend         Start React frontend dev server (port 5173)"
	@echo "  make test             Run all 64 Python tests"
	@echo "  make test-verbose     Run tests with verbose output"
	@echo "  make build            Build production frontend bundle (dist/)"
	@echo "  make demo             Run headless CLI simulation demo"
	@echo "  make install          Install Python dependencies into .venv"
	@echo "  make install-frontend Install frontend npm dependencies"
	@echo "  make lint             Check Python files with ruff (if installed)"
	@echo "  make help             Show this help message"
	@echo "  ─────────────────────────────────────────────────────────────────"
	@echo ""

# ── Backend ───────────────────────────────────────────────────────────────────
backend:
	.venv/bin/python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# ── Frontend ──────────────────────────────────────────────────────────────────
frontend:
	cd frontend && npm run dev

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	.venv/bin/python -m unittest discover -s tests

test-verbose:
	.venv/bin/python -m unittest discover -s tests -v

# ── Build ─────────────────────────────────────────────────────────────────────
build:
	cd frontend && npm run build

# ── CLI Demo ──────────────────────────────────────────────────────────────────
demo:
	.venv/bin/python run_railoptix.py

# ── Install ───────────────────────────────────────────────────────────────────
install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r backend/requirements.txt

install-frontend:
	cd frontend && npm install

# ── Lint ──────────────────────────────────────────────────────────────────────
lint:
	.venv/bin/ruff check backend/ tests/ run_railoptix.py 2>/dev/null || \
		echo "ruff not installed — run: .venv/bin/pip install ruff"
