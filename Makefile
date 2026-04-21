# Makefile for Choir Attendance Server (Backend)

SHELL := /bin/bash

.PHONY: install run dev clean migrations migrate test coverage

# Default port
PORT ?= 8001
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn

# Install backend dependencies
install:
	@echo "Installing backend dependencies..."
	source $(VENV)/bin/activate && $(PIP) install -r requirements.txt

# Run in production mode
run:
	@echo "Starting production server on port $(PORT)..."
	source $(VENV)/bin/activate && $(UVICORN) app.server:app --host 0.0.0.0 --port $(PORT)

# Start backend in development mode (auto-reload)
dev:
	source $(VENV)/bin/activate && PYTHONPATH=. $(PYTHON) app/scripts/create_db.py && PYTHONPATH=. $(UVICORN) app.server:app --reload --host 0.0.0.0 --port $(PORT)

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleaned up."

# Database Migrations

# Create a new migration
# Usage: make migrations m="Your message"
migrations:
	source $(VENV)/bin/activate && $(VENV)/bin/alembic revision --autogenerate -m "$(m)"

# Run migrations
# Usage: make migrate [cmd="upgrade head"]
migrate:
	source $(VENV)/bin/activate && $(VENV)/bin/alembic $(or $(cmd),upgrade head)

# Testing

# Run all tests
test:
	source $(VENV)/bin/activate && $(VENV)/bin/pytest tests/ -v

# Run tests with coverage report
coverage:
	source $(VENV)/bin/activate && $(VENV)/bin/pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html:htmlcov --cov-config=pyproject.toml

