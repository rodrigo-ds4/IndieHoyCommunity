"""
FastAPI Backend - Entry Point
Main application setup and configuration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import create_tables
from app.api.routes import api_router


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
app = FastAPI(
    title="Charro Bot API",
    description="Chatbot + Decision Agent for Show Discounts",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
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

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "🤠 Charro Bot API is running!",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check for Docker/monitoring"""
    return {
        "status": "healthy",
        "service": "charro-bot-api"
    } 