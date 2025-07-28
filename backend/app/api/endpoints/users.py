"""
User Endpoints
Email validation and user checks for the discount request form
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database import User, SupervisionQueue
from app.models.forms import EmailValidationRequest, EmailValidationResponse

router = APIRouter()


@router.post("/validate-email", response_model=EmailValidationResponse)
async def validate_user_email(
    request: EmailValidationRequest, db: Session = Depends(get_db)
):
    """
    Validates if a user exists, is active, and if they don't already have a pending
    request for the specified show.
    """
    user = db.query(User).filter(User.email == request.user_email).first()

    if not user:
        return EmailValidationResponse(
            exists=False,
            can_request=False,
            message="El email no se encuentra en nuestra base de datos de miembros.",
        )

    if not user.subscription_active or not user.monthly_fee_current:
        return EmailValidationResponse(
            exists=True,
            can_request=False,
            user_name=user.name,
            message="Tu suscripción no está activa o tienes un pago pendiente. Por favor, regulariza tu situación.",
        )

    existing_request = db.query(SupervisionQueue).filter(
        SupervisionQueue.user_email == request.user_email,
        SupervisionQueue.show_id == request.show_id,
        SupervisionQueue.status.in_(['pending', 'approved', 'sent'])
    ).first()

    if existing_request:
        return EmailValidationResponse(
            exists=True,
            can_request=False,
            user_name=user.name,
            message="⚠️ Ya tienes una solicitud en proceso para este show. Revisa tu email o espera la aprobación."
        )

    return EmailValidationResponse(
        exists=True,
        can_request=True,
        user_name=user.name,
        message="Usuario validado correctamente.",
    )

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