"""
Discount Endpoints (Updated for LangChain Agent)
Handles discount requests with LangChain agent processing
"""

from fastapi import APIRouter, HTTPException, Depends

from app.models.forms import DiscountRequest, DiscountResponse, AgentReprocessRequest
from app.services.discount_service import DiscountService
from app.services.langchain_agent_service import LangChainAgentService  # 🧪 Para test de Ollama
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

def get_discount_service(db: Session = Depends(get_db)) -> DiscountService:
    return DiscountService(db)


@router.post("/request", response_model=DiscountResponse)
async def request_discount(
    request: DiscountRequest,
    discount_service: DiscountService = Depends(get_discount_service)
):
    """
    Process discount request using LangChain Agent
    
    NEW FLOW:
    1. LangChain agent queries database for validation
    2. Agent makes decision based on business rules + AI reasoning
    3. Agent generates email (approval or rejection)
    4. Everything goes to human supervision queue
    5. Human approves with one click or modifies
    """
    try:
        decision = await discount_service.process_request(request)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inspect/{request_id}")
async def inspect_request_data(
    request_id: int,
    db: Session = Depends(get_db)
):
    """
    DEBUG: Show exactly what data was received and stored
    """
    from app.models.database import DiscountRequest as DBDiscountRequest, User
    
    db_request = db.query(DBDiscountRequest).filter(DBDiscountRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    user = db.query(User).filter(User.id == db_request.user_id).first()
    
    return {
        "request_id": db_request.id,
        "received_data": {
            "user_id": db_request.user_id,
            "user_name_from_db": user.name if user else "Not found",
            "user_email_from_db": user.email if user else "Not found",
            "show_id": db_request.show_id,
            "approved": db_request.approved,
            "human_approved": db_request.human_approved,
            "other_data": db_request.other_data,  # Here's the form data!
            "request_date": db_request.request_date,
            "agent_approval_date": db_request.agent_approval_date
        },
        "form_data_extracted": db_request.other_data if db_request.other_data else "No data"
    }


@router.get("/status/{request_id}")
async def get_discount_status(
    request_id: str,
    discount_service: DiscountService = Depends(get_discount_service)
):
    """Check status of discount request with agent details"""
    try:
        status = await discount_service.get_status(request_id) 
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail="Request not found")


@router.post("/reprocess/{request_id}")
async def reprocess_with_agent(
    request_id: int,
    reprocess_request: AgentReprocessRequest,
    discount_service: DiscountService = Depends(get_discount_service)
):
    """
    Reprocess a request with the LangChain agent
    Useful when human reviewer wants a second opinion
    """
    try:
        result = await discount_service.reprocess_with_agent(
            request_id=request_id,
            additional_context=reprocess_request.additional_context
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/stats")
async def get_agent_performance_stats(
    discount_service: DiscountService = Depends(get_discount_service)
):
    """
    Get LangChain agent performance statistics
    Shows agent success rate, confidence, approval patterns
    """
    try:
        stats = await discount_service.get_agent_stats()
        return {
            "agent_performance": stats,
            "description": "LangChain Agent Performance Metrics",
            "model_used": "llama3 via Ollama"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test/agent-database")
async def test_agent_database_access(
    test_email: str = "test@example.com",
    test_show_id: int = 1,
    discount_service: DiscountService = Depends(get_discount_service)
):
    """
    Test endpoint to verify agent can access database
    Only for development/debugging
    """
    try:
        # This would test the agent's database access
        from app.services.langchain_agent_service import LangChainAgentService
        
        agent_service = LangChainAgentService(discount_service.db)
        
        # Test database tool directly
        user_info = agent_service.db_tool._get_user_info(test_email)
        show_info = agent_service.db_tool._get_show_info(test_show_id)
        
        return {
            "database_access": "success",
            "user_test": user_info,
            "show_test": show_info,
            "note": "This endpoint is for testing only"
        }
    except Exception as e:
        return {
            "database_access": "error",
            "error": str(e),
            "note": "Check database connection and data"
        } 

@router.get("/test-ollama")
async def test_ollama_connection(db: Session = Depends(get_db)):
    """
    🧪 ENDPOINT DE PRUEBA: Verificar conexión con Ollama
    """
    try:
        agent_service = LangChainAgentService(db)
        result = await agent_service.test_llm_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing Ollama: {str(e)}") 