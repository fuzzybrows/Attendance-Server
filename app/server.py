import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse

import app.models
from app.settings import settings as app_settings
from app.core.database import engine
from app.core.logging_config import setup_logging
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.websocket import attendance_ws
from app.routers import auth, members, sessions, attendance, statistics, qr_attendance, calendar, google_auth, session_templates

# Setup logging before creating app or during startup
setup_logging()

logger = logging.getLogger("main")

# models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting background services...", extra={"type": "app_lifecycle", "action": "startup"})
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down background services...", extra={"type": "app_lifecycle", "action": "shutdown"})
    stop_scheduler()

app = FastAPI(title="Choir Attendance Server", lifespan=lifespan)

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

# Add any additional origins from environment variable
if app_settings.cors_origins:
    origins.extend([o.strip() for o in app_settings.cors_origins.split(",") if o.strip()])

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
app.include_router(calendar.router)
app.include_router(google_auth.router)
app.include_router(session_templates.router)

@app.api_route("/health", methods=["GET", "HEAD"], response_class=PlainTextResponse, status_code=200)
def health_check():
    return "OK"

@app.websocket("/ws/attendance/{session_id}")
async def attendance_websocket(websocket: WebSocket, session_id: int):
    await attendance_ws.connect(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        attendance_ws.disconnect(websocket, session_id)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={"type": "unhandled_exception", "path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )
