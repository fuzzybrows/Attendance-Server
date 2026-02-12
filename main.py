from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import models
from database import engine
from routers import auth, members, sessions, attendance, statistics, qr_attendance
from logging_config import setup_logging

# Setup logging before creating app or during startup
setup_logging()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Choir Attendance Server")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(members.router)
app.include_router(sessions.router)
app.include_router(attendance.router)
app.include_router(statistics.router)
app.include_router(qr_attendance.router)

# Serve static files from the React build
frontend_path = os.path.join(os.getcwd(), "frontend", "dist")

if not os.path.exists(frontend_path):
    os.makedirs(frontend_path)

app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    # This serves as a catch-all for React routing if needed
    file_path = os.path.join(frontend_path, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_path, "index.html"))
