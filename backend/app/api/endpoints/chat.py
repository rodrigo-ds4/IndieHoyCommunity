"""
Chat Endpoints
Handles chatbot conversation and LLM interaction
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.models.chat import ChatRequest, ChatResponse, ChatHistory
from app.services.llm_service import LLMService
from app.services.chat_service import ChatService

router = APIRouter()

# Dependency injection (similar to Django views)
def get_llm_service() -> LLMService:
    return LLMService()

def get_chat_service() -> ChatService:
    return ChatService()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    llm_service: LLMService = Depends(get_llm_service),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Send a message to Charro Bot and get response
    
    Similar to a Django view but with automatic:
    - Input validation (ChatRequest)
    - Output validation (ChatResponse)  
    - Dependency injection
    - API documentation
    """
    try:
        # Process message through chat service
        response = await chat_service.process_message(
            message=request.message,
            user_id=request.user_id,
            context=request.context
        )
        
        return ChatResponse(
            response=response.content,
            user_id=request.user_id,
            timestamp=response.timestamp,
            confidence=response.confidence
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}", response_model=List[ChatHistory])
async def get_chat_history(
    user_id: str,
    limit: int = 50,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get chat history for a user"""
    try:
        history = await chat_service.get_history(user_id, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{user_id}")
async def clear_chat_history(
    user_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Clear chat history for a user"""
    try:
        await chat_service.clear_history(user_id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 