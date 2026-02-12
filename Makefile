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
	source $(VENV)/bin/activate && $(UVICORN) main:app --host 0.0.0.0 --port $(PORT)

# Start backend in development mode (auto-reload)
dev-backend:
	source $(VENV)/bin/activate && $(UVICORN) main:app --reload --host 0.0.0.0 --port $(PORT)

# Start frontend in development mode
dev-frontend:
	cd frontend && npm run dev

# Clean up
clean:
	rm -rf frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleaned up."
