"""
FastAPI Backend - Entry Point
Main application setup and configuration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import create_tables
from app.api.routes import api_router
from app.middleware.security import security_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events (startup/shutdown)
    Replaces @app.on_event("startup") / @app.on_event("shutdown")
    """
    # Startup logic
    print("🎵 Starting IndieHOY Community Platform...")
    print("=" * 50)
    print(f"🔧 Environment: {settings.ENVIRONMENT}")
    print(f"🐳 Ollama URL: {settings.OLLAMA_URL}")
    print(f"🗄️ Database URL: {settings.DATABASE_URL}")
    print("=" * 50)
    
    # Create database tables and populate if needed
    try:
        import os
        
        # 🗑️ RECREAR DB: Eliminar DB existente para forzar recreación con nueva estructura (campo img)
        db_file = "./data/charro_bot.db"
        if os.path.exists(db_file):
            print("🗑️ Removing existing database to recreate with new structure (img field)...")
            os.remove(db_file)
            print("✅ Old database removed")
        
        create_tables()
        print("✅ Database tables created with new structure")
        
        # Siempre poblar después de recrear
        print("🔄 Populating database with new show data...")
        import subprocess
        result = subprocess.run(["python", "populate_database.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Database populated successfully with new shows")
        else:
            print(f"❌ Error populating database: {result.stderr}")
                
    except Exception as e:
        print(f"❌ Database setup error: {e}")
    
    yield  # Application runs here
    
    # Shutdown logic
    print("👋 Shutting down IndieHOY Community Platform...")


# FastAPI application instance
# 🔒 Ocultar docs en producción por seguridad
docs_url = "/docs" if settings.ENVIRONMENT == "development" else None
redoc_url = "/redoc" if settings.ENVIRONMENT == "development" else None

app = FastAPI(
    title=settings.APP_NAME,
    description="🎵 Complete community management platform for IndieHOY - User subscriptions, discount requests, and member benefits",
    version=settings.VERSION,
    docs_url=docs_url,  # Solo en desarrollo
    redoc_url=redoc_url,  # Solo en desarrollo
    lifespan=lifespan
)

# CORS middleware (for frontend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🛡️ Security middleware (authentication + protection)
# app.middleware("http")(security_middleware)  # Temporalmente desactivado

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files for supervision dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Redirect to discount request form"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/request")


@app.get("/health")
async def health_check():
    """Health check for Docker/monitoring"""
    return {
        "status": "healthy",
        "service": "charro-bot-api"
    }


@app.get("/supervision")
async def supervision_dashboard():
    """Serve supervision dashboard"""
    from fastapi.responses import FileResponse
    return FileResponse("static/supervision.html")


@app.get("/request")
async def request_discount_form():
    """Serve discount request form"""
    from fastapi.responses import FileResponse
    return FileResponse("static/request-discount.html")


@app.get("/register")
async def user_registration_form():
    """Serve user registration form"""
    from fastapi.responses import FileResponse
    return FileResponse("static/register.html")

@app.get("/users-admin")
async def serve_users_admin():
    """Serve users administration page"""
    from fastapi.responses import FileResponse
    return FileResponse("static/users-admin.html") 