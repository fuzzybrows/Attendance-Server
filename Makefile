# Makefile for Choir Attendance Server

SHELL := /bin/bash

.PHONY: install build-frontend run dev-backend dev-frontend clean

# Default port
PORT ?= 8001
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn

# Install all dependencies
install:
	@echo "Installing backend dependencies..."
	source $(VENV)/bin/activate && $(PIP) install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Build the React frontend
build-frontend:
	@echo "Building frontend..."
	cd frontend && npm run build

# Run in development mode (watch both frontend and backend)
run-dev:
	@echo "Starting development servers..."
	@trap 'kill %1; kill %2' SIGINT; \
	$(MAKE) dev-backend & \
	$(MAKE) dev-frontend & \
	wait

# Run in production mode (build then start)
run: build-frontend
	@echo "Starting production server on port $(PORT)..."
	cd backend && source ../$(VENV)/bin/activate && ../$(UVICORN) main:app --host 0.0.0.0 --port $(PORT)

# Start backend in development mode (auto-reload)
dev-backend:
	cd backend && source ../$(VENV)/bin/activate && ../$(PYTHON) scripts/create_db.py && ../$(UVICORN) main:app --reload --host 0.0.0.0 --port $(PORT)

# Start frontend in development mode
dev-frontend:
	cd frontend && npm run dev -- --open

# Clean up
clean:
	rm -rf frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleaned up."

# Database Migrations

# Create a new migration
# Usage: make migrations m="Your message"
migrations:
	cd backend && source ../$(VENV)/bin/activate && ../$(VENV)/bin/alembic revision --autogenerate -m "$(m)"

# Run migrations
# Usage: make migrate [cmd="upgrade head"]
# Examples:
#   make migrate                # Upgrade to head
#   make migrate cmd="downgrade -1"  # Downgrade 1 step
migrate:
	cd backend && source ../$(VENV)/bin/activate && ../$(VENV)/bin/alembic $(or $(cmd),upgrade head)

