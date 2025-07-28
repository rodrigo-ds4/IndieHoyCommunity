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
    print("🚀 Starting Charro Bot Backend...")
    print(f"🔧 Environment: {settings.ENVIRONMENT}")
    print(f"🐳 Ollama URL: {settings.OLLAMA_URL}")
    print(f"🗄️ Database URL: {settings.DATABASE_URL}")
    
    # Create database tables
    try:
        create_tables()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Database setup error: {e}")
    
    yield  # Application runs here
    
    # Shutdown logic
    print("👋 Shutting down Charro Bot Backend...")


# FastAPI application instance
# 🔒 Ocultar docs en producción por seguridad
docs_url = "/docs" if settings.ENVIRONMENT == "development" else None
redoc_url = "/redoc" if settings.ENVIRONMENT == "development" else None

app = FastAPI(
    title="Charro Bot API",
    description="Chatbot + Decision Agent for Show Discounts",
    version="1.0.0",
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