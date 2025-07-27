"""
Chat Models (Pydantic Schemas)  
Request/response validation models for chatbot conversation
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """Message types for chat classification"""
    DISCOUNT_REQUEST = "discount_request"
    GENERAL_QUERY = "general_query" 
    SHOW_INFO = "show_info"
    GREETING = "greeting"


class ChatRequest(BaseModel):
    """
    Request model for chat messages
    Automatic validation with Pydantic
    """
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    user_id: str = Field(..., description="Unique user identifier")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    
    class Config:
        # Example data for API docs
        json_schema_extra = {
            "example": {
                "message": "Hola, ¿puedo obtener un descuento para el show de mañana?",
                "user_id": "user_123",
                "context": {"show_id": "show_456", "previous_purchases": 2}
            }
        }


class ChatResponse(BaseModel):
    """
    Response model for chat messages
    Ensures consistent API responses
    """
    response: str = Field(..., description="Bot response message")
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    message_type: Optional[MessageType] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Response confidence score")
    suggested_actions: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "¡Hola! Claro, puedo ayudarte con información sobre descuentos.",
                "user_id": "user_123",
                "timestamp": "2024-01-20T10:30:00",
                "message_type": "discount_request",
                "confidence": 0.95,
                "suggested_actions": ["check_eligibility", "view_shows"]
            }
        }


class ChatHistory(BaseModel):
    """Chat history entry"""
    id: int
    user_id: str
    message: str
    response: str
    timestamp: datetime
    message_type: Optional[MessageType] = None 