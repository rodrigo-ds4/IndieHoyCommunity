"""
Health Check Endpoints
For monitoring and Docker health checks
"""

from fastapi import APIRouter, HTTPException
import httpx
from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "charro-bot-api"}


@router.get("/ollama")
async def ollama_health():
    """Check Ollama connectivity"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                return {"status": "healthy", "ollama": "connected"}
            else:
                raise HTTPException(status_code=503, detail="Ollama not responding")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama connection failed: {str(e)}")


@router.get("/database")
async def database_health():
    """Check database connectivity"""
    # TODO: Implement database health check
    return {"status": "healthy", "database": "connected"} 