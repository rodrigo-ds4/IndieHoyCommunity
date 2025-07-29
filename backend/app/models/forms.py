"""
Form Models (Pydantic Schemas)
Request/response validation models for web forms
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime


class DiscountRequest(BaseModel):
    """
    Model for discount requests through web form
    """
    user_name: str = Field(..., min_length=2, max_length=100)
    user_email: EmailStr
    show_id: int = Field(..., gt=0, description="The unique ID of the show being requested")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_name": "Juan Pérez",
                "user_email": "juan@example.com", 
                "show_id": 1,
            }
        }


class EmailValidationRequest(BaseModel):
    user_email: EmailStr
    show_id: int = Field(..., gt=0, description="The unique ID of the show to check for duplicates")


class EmailValidationResponse(BaseModel):
    exists: bool
    can_request: bool
    user_name: Optional[str] = None
    message: str


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


class SupervisionFilters(BaseModel):
    """Filtros para la cola de supervisión"""
    status: Optional[str] = None  # pending, approved, rejected, sent
    user_email: Optional[str] = None
    venue: Optional[str] = None
    show_title: Optional[str] = None  
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None    # YYYY-MM-DD
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica"""
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool 