"""
Discount Endpoints (Updated for Simple Deterministic Logic)
Handles discount requests with deterministic logic
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import uuid

from app.models.forms import DiscountRequest, DiscountResponse
from app.services.simple_discount_service import SimpleDiscountService
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

def get_discount_service(db: Session = Depends(get_db)) -> SimpleDiscountService:
    return SimpleDiscountService(db)


@router.post("/request", response_model=DiscountResponse)
async def request_discount(
    request: DiscountRequest,
    discount_service: SimpleDiscountService = Depends(get_discount_service)
):
    """
    🎫 Procesar solicitud de descuento
    
    Flujo determinístico:
    1. PreFilter: Validar usuario, suscripción, pagos
    2. Validar show y disponibilidad de descuentos
    3. Generar email con template
    4. Enviar a cola de supervisión humana
    
    Args:
        request: Datos de la solicitud de descuento
        
    Returns:
        DiscountResponse: Resultado del procesamiento
    """
    try:
        # Convertir el objeto Pydantic a diccionario
        request_data = request.dict()
        # Generar un request_id único
        request_data["request_id"] = str(uuid.uuid4())
        result = await discount_service.process_discount_request(request_data)
        
        # Adaptar la respuesta del servicio al modelo DiscountResponse
        return {
            "approved": result.get("decision") == "approved",
            "discount_percentage": result.get("discount_percentage"),
            "reason": result.get("reasoning", "Procesamiento completado"),
            "request_id": result.get("queue_id", 0),
            "expiry_date": result.get("expiry_date"),
            "terms": result.get("terms", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing discount request: {str(e)}")


@router.get("/health")
async def discount_health():
    """Health check para el servicio de descuentos"""
    return {
        "service": "discount_service",
        "status": "healthy",
        "version": "2.0_simple_deterministic",
        "timestamp": datetime.now().isoformat()
    } 