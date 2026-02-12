from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas
from database import get_db
from auth import get_password_hash, verify_password, create_access_token
from services.twilio import send_sms_verification, send_email_verification, check_verification

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

@router.post("/login")
def login(data: schemas.MemberLogin, db: Session = Depends(get_db)):
    # Find member by email or phone
    member = db.query(models.Member).filter(
        (models.Member.email == data.login) | (models.Member.phone_number == data.login)
    ).first()
    
    if not member or not verify_password(data.password, member.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if verification is needed
    is_email = "@" in data.login
    is_verified = member.email_verified if is_email else member.phone_number_verified
    
    if not is_verified:
        # Use Twilio Verify to send verification code
        if is_email:
            send_email_verification(member.email)
        else:
            send_sms_verification(member.phone_number)
        return {"status": "unverified", "method": "email" if is_email else "phone"}
    
    access_token = create_access_token(data={"sub": member.email})
    return {"access_token": access_token, "token_type": "bearer", "member": member}

@router.post("/verify-otp")
def verify_otp(data: schemas.OTPVerification, db: Session = Depends(get_db)):
    # Use Twilio Verify to check the code
    if not check_verification(data.login, data.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Find member and mark verified
    member = db.query(models.Member).filter(
        (models.Member.email == data.login) | (models.Member.phone_number == data.login)
    ).first()
    
    if "@" in data.login:
        member.email_verified = True
    else:
        member.phone_number_verified = True
    
    db.commit()
    
    access_token = create_access_token(data={"sub": member.email})
    return {"access_token": access_token, "token_type": "bearer", "member": member}

@router.post("/forgot-password")
def forgot_password(login: str, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(
        (models.Member.email == login) | (models.Member.phone_number == login)
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use Twilio Verify to send verification code
    if "@" in login:
        send_email_verification(member.email)
    else:
        send_sms_verification(member.phone_number)
    return {"status": "otp_sent"}

@router.post("/reset-password")
def reset_password(data: schemas.OTPVerification, new_password: str, db: Session = Depends(get_db)):
    # Use Twilio Verify to check the code
    if not check_verification(data.login, data.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    member = db.query(models.Member).filter(
        (models.Member.email == data.login) | (models.Member.phone_number == data.login)
    ).first()
    
    member.password_hash = get_password_hash(new_password)
    db.commit()
    return {"status": "password_reset_success"}

