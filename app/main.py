from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from settings import settings as app_settings
import models
from database import engine
from routers import auth, members, sessions, attendance, statistics, qr_attendance
from logging_config import setup_logging

# Setup logging before creating app or during startup
setup_logging()

# models.Base.metadata.create_all(bind=engine)

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

# Static files serving removed - frontend is now separate

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("main")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={"type": "unhandled_exception", "path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

