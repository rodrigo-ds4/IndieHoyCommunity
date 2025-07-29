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
        
        # URL por defecto para shows sin imagen específica
        default_img = "https://indiehoy.com/wp-content/uploads/2024/05/comunidad-logo-blanco-1.png"
        
        results = []
        for show in shows:
            remaining_discounts = show.get_remaining_discounts(db)
            
            # Determinar estado de descuentos (disponible/agotado)
            discount_status = "Descuentos disponibles" if remaining_discounts > 0 else "Descuentos agotados"
            
            # Obtener ciudad y discount_type de other_data
            city = show.other_data.get("city", "Ciudad TBD") if show.other_data else "Ciudad TBD"
            discount_type = show.other_data.get("discount_type", "N/A") if show.other_data else "N/A"
            
            results.append({
                "id": show.id,
                "title": show.title,
                "artist": show.artist,
                "venue": show.venue,
                "img": show.img or default_img,  # Usar imagen por defecto si no hay específica
                "show_date": show.show_date.strftime("%Y-%m-%d") if show.show_date else "Fecha TBD",
                "remaining_discounts": remaining_discounts,
                "discount_status": discount_status,  # Nuevo: estado de descuentos
                "city": city,  # Nuevo: ciudad
                "discount_type": discount_type,  # Nuevo: tipo de descuento
                "display_text": f"{show.title} - {show.artist} - {show.venue}",
                "simple_info": f"{city} - {show.title}/{show.artist} - {show.show_date.strftime('%Y-%m-%d') if show.show_date else 'Fecha TBD'} - {discount_type}"
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