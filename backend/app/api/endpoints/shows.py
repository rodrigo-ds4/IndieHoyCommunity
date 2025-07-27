"""
Shows Endpoints
Real-time show search for the discount request form
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.database import Show

router = APIRouter()

@router.get("/search")
async def search_shows(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    🔍 Búsqueda en tiempo real de shows
    
    - **q**: Término de búsqueda (mínimo 2 caracteres)
    - **limit**: Máximo número de resultados (1-50)
    """
    try:
        # Search in title, artist, and venue
        shows = db.query(Show).filter(
            Show.active == True,
            (Show.title.ilike(f"%{q}%") | 
             Show.artist.ilike(f"%{q}%") | 
             Show.venue.ilike(f"%{q}%"))
        ).limit(limit).all()
        
        results = []
        for show in shows:
            remaining_discounts = show.get_remaining_discounts(db)
            if remaining_discounts > 0:  # Only shows with available discounts
                results.append({
                    "id": show.id,
                    "title": show.title,
                    "artist": show.artist,
                    "venue": show.venue,
                    "show_date": show.show_date.strftime("%Y-%m-%d") if show.show_date else "Fecha TBD",
                    "price": show.other_data.get("price", 0) if show.other_data else 0,
                    "remaining_discounts": remaining_discounts,
                    "display_text": f"{show.title} - {show.artist} - {show.venue}",
                    "full_info": f"{show.title} por {show.artist} en {show.venue} - ${show.other_data.get('price', 'N/A')} ({remaining_discounts} descuentos disponibles)"
                })
        
        return {
            "success": True,
            "results": results,
            "count": len(results),
            "query": q
        }
        
    except Exception as e:
        return {
            "success": False,
            "results": [],
            "count": 0,
            "error": str(e)
        }

@router.get("/available")
async def get_available_shows(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    📋 Obtener todos los shows disponibles con descuentos
    """
    try:
        shows = db.query(Show).filter(Show.active == True).limit(limit).all()
        
        results = []
        for show in shows:
            remaining_discounts = show.get_remaining_discounts(db)
            if remaining_discounts > 0:
                results.append({
                    "id": show.id,
                    "title": show.title,
                    "artist": show.artist,
                    "venue": show.venue,
                    "show_date": show.show_date.strftime("%Y-%m-%d") if show.show_date else "Fecha TBD",
                    "price": show.other_data.get("price", 0) if show.other_data else 0,
                    "remaining_discounts": remaining_discounts,
                    "genre": show.other_data.get("genre", "N/A") if show.other_data else "N/A"
                })
        
        return {
            "success": True,
            "shows": results,
            "count": len(results)
        }
        
    except Exception as e:
        return {
            "success": False,
            "shows": [],
            "count": 0,
            "error": str(e)
        } 