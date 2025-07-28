from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import re

# 🔒 Endpoints que requieren autenticación
PROTECTED_ENDPOINTS = [
    r'^/api/v1/supervision.*',
    r'^/api/v1/admin.*',
    r'^/docs.*',
    r'^/redoc.*',
    r'^/openapi\.json$'
]

# 🌐 Endpoints públicos (no requieren auth)
PUBLIC_ENDPOINTS = [
    r'^/api/v1/auth/login$',
    r'^/api/v1/auth/verify$',
    r'^/api/v1/health.*',
    r'^/static/login\.html$',
    r'^/static/request-discount\.html$',
    r'^/$',
    r'^/favicon\.ico$'
]

def is_protected_endpoint(path: str) -> bool:
    """Verificar si un endpoint requiere autenticación"""
    # Primero verificar si es público
    for pattern in PUBLIC_ENDPOINTS:
        if re.match(pattern, path):
            return False
    
    # Luego verificar si está protegido
    for pattern in PROTECTED_ENDPOINTS:
        if re.match(pattern, path):
            return True
    
    return False

async def verify_session_token(request: Request) -> dict:
    """Verificar token de sesión desde cookie"""
    from app.api.endpoints.auth import active_sessions, is_valid_session
    
    session_token = request.cookies.get("session_token")
    
    if not session_token or not is_valid_session(session_token):
        return None
    
    return active_sessions.get(session_token)

async def security_middleware(request: Request, call_next):
    """
    🛡️ Middleware de seguridad
    - Protege endpoints sensibles
    - Verifica autenticación
    - Oculta docs en producción
    """
    path = request.url.path
    
    # 🔒 Verificar si el endpoint está protegido
    if is_protected_endpoint(path):
        session_data = await verify_session_token(request)
        
        if not session_data:
            # Si es una API, devolver JSON
            if path.startswith('/api/'):
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "detail": "Authentication required",
                        "error_code": "UNAUTHORIZED"
                    }
                )
            
            # Si es una página, redirigir al login
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/static/login.html", status_code=302)
    
    # 🚫 Bloquear docs en producción
    from app.core.config import settings
    if settings.ENVIRONMENT != "development" and path in ["/docs", "/redoc", "/openapi.json"]:
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
    
    # Continuar con la request
    response = await call_next(request)
    
    # 🔒 Headers de seguridad adicionales
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response 