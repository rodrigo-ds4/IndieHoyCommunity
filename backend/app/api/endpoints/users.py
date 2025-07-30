"""
User Endpoints
Email validation, user checks and user registration
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from sqlalchemy import or_, func
import re

from app.core.database import get_db
from app.models.database import User, SupervisionQueue, EmailTemplate
from app.models.forms import EmailValidationRequest, EmailValidationResponse
from app.services.smtp_email_service import SMTPEmailService

# Importar funciones de autenticación
from app.api.endpoints.auth import is_valid_session

router = APIRouter()

# ========================================
# 🔐 DEPENDENCIA DE AUTENTICACIÓN
# ========================================

def verify_admin_session(request: Request):
    """Verificar que el usuario esté autenticado como admin"""
    session_token = request.cookies.get("session_token")
    
    if not session_token or not is_valid_session(session_token):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    
    return session_token

# ========================================
# 📝 MODELOS PARA REGISTRO DE USUARIOS
# ========================================

class EmailCheckRequest(BaseModel):
    email: EmailStr

class EmailCheckResponse(BaseModel):
    exists: bool
    message: str

class UserRegistrationRequest(BaseModel):
    name: str
    email: EmailStr
    dni: Optional[int] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    how_did_you_find_us: Optional[str] = None
    favorite_music_genre: Optional[str] = None
    
    @validator('name')
    def name_must_be_valid(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('El nombre debe tener al menos 2 caracteres')
        if len(v.strip()) > 100:
            raise ValueError('El nombre no puede tener más de 100 caracteres')
        return v.strip()
    
    @validator('phone')
    def phone_must_be_valid(cls, v):
        if v and v.strip():
            # Permitir formatos: +54 11 1234-5678, 11 1234-5678, 1112345678
            phone_pattern = r'^(\+54\s?)?(\d{2,4}[\s\-]?\d{4}[\s\-]?\d{4}|\d{10,11})$'
            if not re.match(phone_pattern, v.strip()):
                raise ValueError('El teléfono debe tener un formato válido')
            return v.strip()
        return v
    
    @validator('city')
    def city_must_be_valid(cls, v):
        if v and len(v.strip()) > 100:
            raise ValueError('La ciudad no puede tener más de 100 caracteres')
        return v.strip() if v else v

class UserRegistrationResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None

# ========================================
# 🔍 ENDPOINT: VERIFICAR EMAIL
# ========================================

@router.post("/check-email", response_model=EmailCheckResponse)
async def check_email_exists(
    request: EmailCheckRequest, db: Session = Depends(get_db)
):
    """
    🔍 Verificar si un email ya existe en la base de datos
    
    **Uso:** Validación en tiempo real durante el registro
    
    **Respuesta:**
    - `exists`: true si el email ya está registrado
    - `message`: Mensaje descriptivo para mostrar al usuario
    """
    try:
        user = db.query(User).filter(User.email == request.email).first()
        
        if user:
            return EmailCheckResponse(
                exists=True,
                message="Este email ya está registrado en IndieHOY"
            )
        else:
            return EmailCheckResponse(
                exists=False,
                message="Email disponible para registro"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando email: {str(e)}"
        )

# ========================================
# 📝 ENDPOINT: REGISTRAR USUARIO
# ========================================

@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest, db: Session = Depends(get_db)
):
    """
    📝 Registrar un nuevo usuario en IndieHOY
    
    **Validaciones:**
    - Email único (no puede estar ya registrado)
    - DNI único (si se proporciona)
    - Campos requeridos: name, email
    - Formatos válidos para teléfono
    
    **Respuesta:**
    - `success`: true si el registro fue exitoso
    - `message`: Mensaje para mostrar al usuario
    - `user_id`: ID del usuario creado (si fue exitoso)
    """
    try:
        # 1. 🔍 Verificar que el email no exista
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            return UserRegistrationResponse(
                success=False,
                message="Este email ya está registrado. ¿Querés iniciar sesión?"
            )
        
        # 2. 🔍 Verificar que el DNI no exista (si se proporciona)
        if request.dni:
            existing_dni = db.query(User).filter(User.dni == request.dni).first()
            if existing_dni:
                return UserRegistrationResponse(
                    success=False,
                    message="Este DNI ya está registrado en el sistema"
                )
        
        # 3. 📝 Crear nuevo usuario
        new_user = User(
            name=request.name,
            email=request.email,
            dni=request.dni,
            phone=request.phone,
            city=request.city,
            registration_date=datetime.now(),
            how_did_you_find_us=request.how_did_you_find_us,
            favorite_music_genre=request.favorite_music_genre,
            subscription_active=True,  # Suscripción activa (pueden usar la plataforma)
            monthly_fee_current=False,  # ❌ NUEVO: No han pagado hasta que no paguen
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 5. 📧 Enviar email automático con información de pago
        try:
            send_payment_info_email(new_user, db)
        except Exception as e:
            # Log error but don't fail registration
            print(f"❌ Error sending payment info email: {e}")
        
        return UserRegistrationResponse(
            success=True,
            message=f"¡Bienvenido a IndieHOY, {request.name}! Tu cuenta ha sido creada exitosamente. Te enviaremos un email con la información de pago para activar los descuentos.",
            user_id=new_user.id
        )
        
    except ValueError as e:
        # Errores de validación de Pydantic
        return UserRegistrationResponse(
            success=False,
            message=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creando usuario: {str(e)}"
        )

# ========================================
# 📊 ENDPOINT: ESTADÍSTICAS DE USUARIOS
# ========================================

# Función duplicada eliminada - ver función get_user_stats más abajo

# ========================================
# 🔍 ENDPOINT EXISTENTE: VALIDAR EMAIL PARA DESCUENTOS
# ========================================

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


# ========================================
# 👥 MODELOS PARA ADMINISTRACIÓN DE USUARIOS
# ========================================

class UserListItem(BaseModel):
    id: int
    name: str
    email: str
    city: Optional[str]
    phone: Optional[str]
    dni: Optional[int]  # 🔧 Corregido: debe ser int como en la DB
    registration_date: datetime
    subscription_active: bool
    monthly_fee_current: bool
    created_at: datetime
    
    # 💳 Información de pagos
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[float] = None
    total_payments: int = 0
    payment_method: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    success: bool
    users: List[UserListItem]
    pagination: dict
    message: Optional[str] = None

class PaymentStatusUpdate(BaseModel):
    monthly_fee_current: bool

class PaymentStatusResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserListItem] = None


# ========================================
# 👥 ENDPOINTS DE ADMINISTRACIÓN DE USUARIOS
# ========================================

@router.get("/list", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    email: Optional[str] = Query(None, description="Filtrar por email"),
    payment_status: Optional[str] = Query(None, description="Filtrar por estado de pago: current, overdue"),
    city: Optional[str] = Query(None, description="Filtrar por ciudad"),
    db: Session = Depends(get_db),
    session: str = Depends(verify_admin_session)
):
    """
    📋 Listar usuarios con filtros y paginación
    """
    try:
        # Construir query base
        query = db.query(User)
        
        # Aplicar filtros
        if email:
            query = query.filter(User.email.ilike(f"%{email}%"))
        
        if payment_status:
            if payment_status == "current":
                query = query.filter(User.monthly_fee_current == True)
            elif payment_status == "overdue":
                query = query.filter(User.monthly_fee_current == False)
        
        if city:
            query = query.filter(User.city.ilike(f"%{city}%"))
        
        # Ordenar por fecha de registro (más recientes primero)
        query = query.order_by(User.registration_date.desc())
        
        # Contar total de elementos
        total_items = query.count()
        
        # Aplicar paginación
        offset = (page - 1) * page_size
        users = query.offset(offset).limit(page_size).all()
        
        # Calcular información de paginación
        total_pages = (total_items + page_size - 1) // page_size
        
        pagination_info = {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_items,
            "page_size": page_size,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
        # 💳 CONVERTIR USUARIOS CON INFORMACIÓN DE PAGOS
        from app.models.database import PaymentHistory
        user_items = []
        
        for user in users:
            # Obtener historial de pagos del usuario
            payments = db.query(PaymentHistory).filter(
                PaymentHistory.user_id == user.id,
                PaymentHistory.confirmed == True  # Solo pagos confirmados
            ).order_by(PaymentHistory.payment_date.desc()).all()
            
            user_dict = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "city": user.city,
                "phone": user.phone,
                "dni": user.dni,  # 🔧 Ya arreglado: mantener como int
                "registration_date": user.registration_date,
                "subscription_active": user.subscription_active,
                "monthly_fee_current": user.monthly_fee_current,
                "created_at": user.created_at,
                "total_payments": len(payments)
            }
            
            # Agregar info del último pago si existe
            if payments:
                last_payment = payments[0]  # Ya está ordenado por fecha desc
                user_dict.update({
                    "last_payment_date": last_payment.payment_date,
                    "last_payment_amount": last_payment.amount_paid,
                    "payment_method": last_payment.payment_method
                })
            
            user_items.append(UserListItem(**user_dict))
        
        return UserListResponse(
            success=True,
            users=user_items,
            pagination=pagination_info,
            message=f"Se encontraron {total_items} usuarios"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar usuarios: {str(e)}")


@router.patch("/{user_id}/payment-status", response_model=PaymentStatusResponse)
async def update_payment_status(
    user_id: int,
    update_data: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    session: str = Depends(verify_admin_session)
):
    """
    💳 Actualizar estado de pago de un usuario
    """
    try:
        # Buscar usuario
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Actualizar estado de pago
        old_status = user.monthly_fee_current
        user.monthly_fee_current = update_data.monthly_fee_current
        user.updated_at = datetime.now()
        
        # 📋 CREAR REGISTRO EN PAYMENT_HISTORY si hay un cambio real
        if old_status != update_data.monthly_fee_current:
            from app.models.database import PaymentHistory
            
            payment_record = PaymentHistory(
                user_id=user.id,
                amount_paid=0.0,  # Será actualizado cuando se integre con MercadoPago
                payment_date=datetime.now(),
                payment_method="admin_update",  # Método especial para cambios manuales
                description=f"Estado cambiado manualmente: {'al día' if update_data.monthly_fee_current else 'pendiente'}",
                confirmed=update_data.monthly_fee_current  # True si al día, False si pendiente
            )
            db.add(payment_record)
        
        db.commit()
        db.refresh(user)
        
        # Mensaje descriptivo
        status_text = "al día" if update_data.monthly_fee_current else "pendiente"
        action_text = "marcado como" if old_status != update_data.monthly_fee_current else "ya estaba"
        
        return PaymentStatusResponse(
            success=True,
            message=f"Usuario {user.name} {action_text} {status_text}",
            user=UserListItem.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar estado de pago: {str(e)}")


@router.get("/stats")
async def get_user_stats(
    db: Session = Depends(get_db),
    session: str = Depends(verify_admin_session)
):
    """
    📊 Obtener estadísticas básicas de usuarios
    """
    try:
        total_users = db.query(User).count()
        users_current = db.query(User).filter(User.monthly_fee_current == True).count()
        users_overdue = db.query(User).filter(User.monthly_fee_current == False).count()
        active_subscriptions = db.query(User).filter(User.subscription_active == True).count()
        
        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "users_current": users_current,
                "users_overdue": users_overdue,
                "active_subscriptions": active_subscriptions,
                "payment_rate": round((users_current / total_users * 100) if total_users > 0 else 0, 1)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")


# ========================================
# 📧 FUNCIÓN PARA ENVÍO DE EMAILS AUTOMÁTICOS
# ========================================

def send_payment_info_email(user: User, db: Session):
    """
    📧 Enviar email automático con información de pago después del registro
    """
    try:
        # 1. Obtener template de email
        template = db.query(EmailTemplate).filter(
            EmailTemplate.template_name == 'payment_info'
        ).first()
        
        if not template:
            print("❌ No se encontró template de información de pago")
            return
        
        # 2. Reemplazar placeholders
        subject = template.subject.replace('{{user_name}}', user.name)
        body = template.body.replace('{{user_name}}', user.name)
        
        # 3. Inicializar servicio de email
        email_service = SMTPEmailService(db_session=db)
        
        # 4. Enviar email (sin supervision_queue_id ya que es automático)
        result = email_service.send_email(
            to_email=user.email,
            subject=subject,
            content=body.replace('\n', '<br>'),  # Convertir a HTML básico
            user_name=user.name,
            supervision_queue_id=None  # Email automático, no requiere supervisión
        )
        
        if result.get('success'):
            print(f"✅ Email de información de pago enviado a {user.email}")
        else:
            print(f"❌ Error enviando email de pago: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error en send_payment_info_email: {e}")
        # No lanzamos excepción para no fallar el registro 