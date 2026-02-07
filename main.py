from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, database
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Choir Attendance Server")

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:5173", # Default Vite port
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/members/", response_model=schemas.Member)
def create_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    db_member = models.Member(name=member.name, email=member.email, nfc_id=member.nfc_id)
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@app.get("/members/", response_model=List[schemas.Member])
def read_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    members = db.query(models.Member).offset(skip).limit(limit).all()
    return members

@app.post("/sessions/", response_model=schemas.Session)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db)):
    db_session = models.Session(title=session.title, type=session.type, date=session.date)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@app.get("/sessions/", response_model=List[schemas.Session])
def read_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sessions = db.query(models.Session).offset(skip).limit(limit).all()
    return sessions

@app.post("/attendance/", response_model=schemas.Attendance)
def mark_attendance(attendance: schemas.AttendanceCreate, db: Session = Depends(get_db)):
    # Verify member and session exist
    member = db.query(models.Member).filter(models.Member.id == attendance.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    session = db.query(models.Session).filter(models.Session.id == attendance.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_attendance = models.Attendance(
        member_id=attendance.member_id,
        session_id=attendance.session_id,
        latitude=attendance.latitude,
        longitude=attendance.longitude,
        submission_type=attendance.submission_type
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

@app.get("/attendance/{session_id}", response_model=List[schemas.Attendance])
def read_attendance(session_id: int, db: Session = Depends(get_db)):
    attendance = db.query(models.Attendance).filter(models.Attendance.session_id == session_id).all()
    return attendance

@app.get("/statistics/overall")
def get_overall_stats(db: Session = Depends(get_db)):
    members = db.query(models.Member).all()
    attendance = db.query(models.Attendance).all()
    sessions = {s.id: s for s in db.query(models.Session).all()}
    
    stats = []
    for member in members:
        member_attendance = [a for a in attendance if a.member_id == member.id]
        total = len(member_attendance)
        prompt = 0
        late = 0
        
        for a in member_attendance:
            session = sessions.get(a.session_id)
            if session and a.timestamp <= session.date:
                prompt += 1
            else:
                late += 1
        
        prompt_rate = (prompt / total * 100) if total > 0 else 0
        
        stats.append({
            "member_id": member.id,
            "name": member.name,
            "total_sessions": total,
            "prompt_count": prompt,
            "late_count": late,
            "prompt_rate": round(prompt_rate, 2)
        })
    
    # Rank by prompt_rate
    stats.sort(key=lambda x: x["prompt_rate"], reverse=True)
    return stats

@app.get("/statistics/member/{member_id}")
def get_member_stats(member_id: int, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
        
    attendance = db.query(models.Attendance).filter(models.Attendance.member_id == member_id).all()
    sessions = {s.id: s for s in db.query(models.Session).all()}
    
    history = []
    for a in attendance:
        session = sessions.get(a.session_id)
        status = "prompt" if session and a.timestamp <= session.date else "late"
        history.append({
            "session_title": session.title if session else "Unknown",
            "timestamp": a.timestamp,
            "status": status,
            "session_date": session.date if session else None
        })
        
    return {
        "member_name": member.name,
        "history": history
    }

# Serve static files from the React build
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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
