import re
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.member import Member
from app.schemas.auth import MemberLogin, LoginResponse, OTPVerification, StatusResponse, Token, ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.member import Member as MemberSchema
from app.core.database import get_db
from app.core.auth import get_password_hash, verify_password, create_access_token, get_current_active_member
from app.services.twilio import send_sms_verification, send_email_verification, check_verification
from app.services.recaptcha import verify_recaptcha
from app.services.rate_limiter import check_login_rate, check_forgot_password_rate
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

@router.post("/login", response_model=LoginResponse)
def login(data: MemberLogin, request: Request, db: Session = Depends(get_db)):
    # Rate limit by IP – protects all clients (web, mobile, API)
    check_login_rate(request)

    logger.info("Login attempt", extra={"type": "login_attempt", "login": data.login})
    
    # Verify reCAPTCHA only if a token was provided (web clients send one, mobile doesn't)
    if data.recaptcha_token and not verify_recaptcha(data.recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA verification failed. Please complete the captcha.")
        
    # Find member by email or phone
    member = db.query(Member).filter(
        (func.lower(Member.email) == data.login) | (Member.phone_number == data.login)
    ).first()
    
    if not member or not verify_password(data.password, member.password_hash) or not member.is_active:
        logger.warning("Login failed - Invalid credentials or disabled", extra={"type": "login_failed", "login": data.login, "reason": "invalid_credentials_or_disabled"})
        raise HTTPException(status_code=401, detail="Invalid credentials or account disabled")
    
    # Check if verification is needed
    is_email = "@" in data.login
    is_verified = member.email_verified if is_email else member.phone_number_verified
    
    if not is_verified:
        # Use Twilio Verify to send verification code
        if is_email:
            send_email_verification(member.email)
        else:
            send_sms_verification(member.phone_number)
        logger.info("User unverified, sent verification code", extra={"type": "verification_sent", "login": data.login, "method": "email" if is_email else "phone"})
        return {"status": "unverified", "method": "email" if is_email else "phone"}
    
    access_token = create_access_token(data={"sub": member.email})
    logger.info("Login successful", extra={"type": "login_success", "login": data.login, "member_id": member.id})
    member_data = MemberSchema.model_validate(member, from_attributes=True)
    return {"access_token": access_token, "token_type": "bearer", "member": member_data}

@router.post("/verify-otp", response_model=Token)
def verify_otp(data: OTPVerification, db: Session = Depends(get_db)):
    # Use Twilio Verify to check the code
    if not check_verification(data.login, data.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Find member and mark verified
    member = db.query(Member).filter(
        (func.lower(Member.email) == data.login) | (Member.phone_number == data.login)
    ).first()
    
    if "@" in data.login:
        member.email_verified = True
    else:
        member.phone_number_verified = True
    
    db.commit()
    
    access_token = create_access_token(data={"sub": member.email})
    return {"access_token": access_token, "token_type": "bearer", "member": member}

@router.post("/forgot-password", response_model=StatusResponse)
def forgot_password(data: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limit by IP
    check_forgot_password_rate(request)

    # Verify reCAPTCHA only if a token was provided
    if data.recaptcha_token and not verify_recaptcha(data.recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA verification failed. Please complete the captcha.")

    member = db.query(Member).filter(
        (func.lower(Member.email) == data.login) | (Member.phone_number == data.login)
    ).first()
    
    if not member:
        return {"status": "If an account matching this email or phone number exists, we'll send reset instructions."}
    
    # Use Twilio Verify to send verification code
    if "@" in data.login:
        send_email_verification(member.email)
    else:
        send_sms_verification(member.phone_number)
    return {"status": "If an account matching this email or phone number exists, we'll send reset instructions."}

@router.post("/reset-password", response_model=StatusResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Use Twilio Verify to check the code
    if not check_verification(data.login, data.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    member = db.query(Member).filter(
        (func.lower(Member.email) == data.login) | (Member.phone_number == data.login)
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$", data.new_password):
        raise HTTPException(
            status_code=400, 
            detail="Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character."
        )
    
    member.password_hash = get_password_hash(data.new_password)
    
    # OTP was verified, so mark the contact method as verified
    if "@" in data.login:
        member.email_verified = True
    else:
        member.phone_number_verified = True
    
    db.commit()
    return {"status": "password_reset_success"}


@router.post("/refresh", response_model=Token)
def refresh_token(
    current_member: Member = Depends(get_current_active_member),
):
    """Issue a fresh JWT for an already-authenticated user.
    
    Called silently by the frontend when the current token is
    nearing expiry, keeping the session alive without requiring
    the user to log in again.
    """
    access_token = create_access_token(data={"sub": current_member.email})
    logger.info("Token refreshed", extra={"type": "token_refresh", "member_id": current_member.id})
    member_data = MemberSchema.model_validate(current_member, from_attributes=True)
    return {"access_token": access_token, "token_type": "bearer", "member": member_data}
