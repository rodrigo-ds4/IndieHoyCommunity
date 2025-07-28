from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel
import hashlib
import os
from datetime import datetime, timedelta

router = APIRouter()

# Credenciales básicas (en producción deberían estar en variables de entorno)
ADMIN_CREDENTIALS = {
    "admin": "admin123",
    "supervisor": "super123",
    "indiehoy": "indie2024"
}

# Sesiones activas (en producción usar Redis o DB)
active_sessions = {}

class LoginRequest(BaseModel):
    username: str
    password: str

def create_session_token(username: str) -> str:
    """Crear token de sesión simple"""
    timestamp = str(datetime.now().timestamp())
    raw_token = f"{username}:{timestamp}:{os.urandom(16).hex()}"
    return hashlib.sha256(raw_token.encode()).hexdigest()

def is_valid_session(token: str) -> bool:
    """Verificar si la sesión es válida"""
    if token not in active_sessions:
        return False
    
    session_data = active_sessions[token]
    # Verificar si la sesión no ha expirado (24 horas)
    if datetime.now() > session_data['expires']:
        del active_sessions[token]
        return False
    
    return True

@router.post("/login")
async def login(login_data: LoginRequest, response: Response):
    """
    🔐 Autenticación básica para acceso al dashboard
    
    Credenciales por defecto:
    - admin / admin123
    - supervisor / super123  
    - indiehoy / indie2024
    """
    username = login_data.username.strip().lower()
    password = login_data.password.strip()
    
    # Verificar credenciales
    if username not in ADMIN_CREDENTIALS or ADMIN_CREDENTIALS[username] != password:
        raise HTTPException(
            status_code=401, 
            detail="Credenciales incorrectas"
        )
    
    # Crear sesión
    session_token = create_session_token(username)
    expires_at = datetime.now() + timedelta(hours=24)
    
    active_sessions[session_token] = {
        'username': username,
        'created': datetime.now(),
        'expires': expires_at
    }
    
    # Establecer cookie de sesión
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=24*60*60,  # 24 horas
        httponly=True,
        secure=False,  # En producción debería ser True (HTTPS)
        samesite="lax"
    )
    
    return {
        "success": True,
        "message": f"Bienvenido {username}",
        "username": username,
        "expires": expires_at.isoformat()
    }

@router.post("/logout")
async def logout(request: Request, response: Response):
    """🚪 Cerrar sesión"""
    session_token = request.cookies.get("session_token")
    
    if session_token and session_token in active_sessions:
        del active_sessions[session_token]
    
    # Limpiar cookie
    response.delete_cookie("session_token")
    
    return {
        "success": True,
        "message": "Sesión cerrada correctamente"
    }

@router.get("/verify")
async def verify_session(request: Request):
    """✅ Verificar si la sesión es válida"""
    session_token = request.cookies.get("session_token")
    
    if not session_token or not is_valid_session(session_token):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    
    session_data = active_sessions[session_token]
    return {
        "success": True,
        "username": session_data['username'],
        "expires": session_data['expires'].isoformat()
    }

@router.get("/sessions")
async def list_active_sessions(request: Request):
    """📊 Listar sesiones activas (solo para debug)"""
    session_token = request.cookies.get("session_token")
    
    if not session_token or not is_valid_session(session_token):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    # Limpiar sesiones expiradas
    current_time = datetime.now()
    expired_tokens = [
        token for token, data in active_sessions.items() 
        if current_time > data['expires']
    ]
    
    for token in expired_tokens:
        del active_sessions[token]
    
    return {
        "success": True,
        "active_sessions": len(active_sessions),
        "sessions": [
            {
                "username": data['username'],
                "created": data['created'].isoformat(),
                "expires": data['expires'].isoformat()
            }
            for data in active_sessions.values()
        ]
    } 