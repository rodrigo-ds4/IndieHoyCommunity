"""
User Endpoints
Email validation and user checks for the discount request form
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.database import User
from pydantic import BaseModel, EmailStr

router = APIRouter()

class EmailValidationRequest(BaseModel):
    email: EmailStr

class EmailValidationResponse(BaseModel):
    exists: bool
    user_name: str = None
    subscription_active: bool = None
    payment_current: bool = None
    message: str = ""

@router.post("/validate-email", response_model=EmailValidationResponse)
async def validate_user_email(
    request: EmailValidationRequest,
    db: Session = Depends(get_db)
):
    """
    🔍 Validate if user email exists and check status
    
    Returns user info if email exists, or error message if not found.
    Used by the discount request form for pre-validation.
    """
    try:
        # Look for user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            return EmailValidationResponse(
                exists=False,
                message="📧 Email no registrado. Por favor verifique que está usando el email correcto o regístrese en nuestra plataforma."
            )
        
        # User exists, check their status
        if not user.subscription_active:
            return EmailValidationResponse(
                exists=True,
                user_name=user.name,
                subscription_active=False,
                payment_current=user.monthly_fee_current,
                message="⚠️ Su suscripción está inactiva. Para solicitar descuentos debe tener una suscripción activa."
            )
        
        if not user.monthly_fee_current:
            return EmailValidationResponse(
                exists=True,
                user_name=user.name,
                subscription_active=True,
                payment_current=False,
                message="💳 Tiene pagos pendientes. Para solicitar descuentos debe estar al día con los pagos."
            )
        
        # All good!
        return EmailValidationResponse(
            exists=True,
            user_name=user.name,
            subscription_active=True,
            payment_current=True,
            message=f"✅ Hola {user.name}! Puede proceder con su solicitud de descuento."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating email: {str(e)}")

@router.get("/check-email")
async def check_email_exists(
    email: str = Query(..., description="Email to check"),
    db: Session = Depends(get_db)
):
    """
    🔍 Simple email existence check (GET endpoint for quick checks)
    """
    try:
        user = db.query(User).filter(User.email == email).first()
        return {
            "exists": user is not None,
            "user_name": user.name if user else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 