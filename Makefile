# Makefile for Choir Attendance Server

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
	$(PIP) install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Build the React frontend
build-frontend:
	@echo "Building frontend..."
	cd frontend && npm run build

# Run the application (Production-like)
run: build-frontend
	@echo "Starting server on port $(PORT)..."
	$(UVICORN) main:app --host 0.0.0.0 --port $(PORT)

# Start backend in development mode (auto-reload)
dev-backend:
	$(UVICORN) main:app --reload --port $(PORT)

# Start frontend in development mode
dev-frontend:
	cd frontend && npm run dev

# Clean up
clean:
	rm -rf frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleaned up."
