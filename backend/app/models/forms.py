"""
Form Models (Pydantic Schemas)
Request/response validation models for web forms
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DiscountRequest(BaseModel):
    """
    Model for discount requests through web form
    """
    user_name: str = Field(..., min_length=2, max_length=100)
    user_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    show_description: str = Field(..., min_length=5, max_length=200, description="Show/artist description (free text)")
    user_history: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "Juan Pérez",
                "user_email": "juan@example.com", 
                "show_description": "Los Piojos en el Luna Park",
                "user_history": {"previous_shows": 3, "loyalty_points": 150}
            }
        }


class DiscountResponse(BaseModel):
    """Response for discount requests"""
    approved: bool
    discount_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    reason: str
    request_id: int = Field(..., description="ID for tracking and human supervision")
    expiry_date: Optional[datetime] = None
    terms: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "approved": True,
                "discount_percentage": 15.0,
                "reason": "Solicitud aprobada por el agente LangChain. Usuario cumple con todos los requisitos y presenta una razón válida.",
                "request_id": 123,
                "expiry_date": "2024-02-01T23:59:59",
                "terms": ["Descuento válido por 7 días", "Sujeto a disponibilidad", "Un descuento por persona"]
            }
        }


class AgentReprocessRequest(BaseModel):
    """Request model for reprocessing with agent"""
    additional_context: str = Field(default="", description="Additional context for reprocessing")
    reviewer_name: str = Field(..., description="Name of person requesting reprocessing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "additional_context": "Usuario es cliente VIP con 5 años de antigüedad",
                "reviewer_name": "Maria Rodriguez"
            }
        } 