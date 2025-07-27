"""
Supervision Endpoints (Updated for LangChain Agent)
Human oversight with enhanced agent information
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.supervision_service import SupervisionService
from app.services.discount_service import DiscountService
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

# Dependencies
def get_supervision_service(db: Session = Depends(get_db)) -> SupervisionService:
    return SupervisionService(db)

def get_discount_service(db: Session = Depends(get_db)) -> DiscountService:
    return DiscountService(db)


class EmailUpdateRequest(BaseModel):
    """Request model for updating email drafts"""
    email_content: str
    reviewer_name: str
    notes: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Request model for final approval"""
    reviewer_name: str
    final_notes: Optional[str] = None


class RejectionRequest(BaseModel):
    """Request model for rejecting requests"""
    reviewer_name: str
    rejection_reason: str


@router.get("/dashboard")
async def get_supervision_dashboard(
    supervision_service: SupervisionService = Depends(get_supervision_service),
    discount_service: DiscountService = Depends(get_discount_service)
):
    """
    Enhanced supervision dashboard with LangChain agent metrics
    """
    try:
        # Get traditional supervision stats
        supervision_stats = await supervision_service.get_supervision_stats()
        
        # Get agent performance stats
        agent_stats = await discount_service.get_agent_stats()
        
        # Get recent requests
        pending_reviews = await supervision_service.get_pending_reviews(limit=20)
        
        return {
            "supervision_stats": supervision_stats,
            "agent_performance": agent_stats,
            "recent_requests": pending_reviews,
            "dashboard_title": "🔍 Supervisión de Descuentos - Charro Bot (LangChain Agent)",
            "system_info": {
                "agent_enabled": True,
                "model": "llama3",
                "processing_mode": "langchain_agent"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def get_pending_requests(
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    supervision_service: SupervisionService = Depends(get_supervision_service)
):
    """Get pending requests with agent decision details"""
    try:
        requests = await supervision_service.get_pending_reviews(
            limit=limit,
            status_filter=status
        )
        
        # Enhance with agent information
        enhanced_requests = []
        for req in requests:
            enhanced_req = req.copy()
            # Add agent-specific fields
            enhanced_req["agent_processed"] = req.get("validation_checks", {}).get("processed_by") == "langchain_agent"
            enhanced_req["agent_confidence"] = req.get("confidence_score", 0) * 100 if req.get("confidence_score") else 0
            enhanced_requests.append(enhanced_req)
        
        return {
            "requests": enhanced_requests,
            "count": len(enhanced_requests),
            "filters_applied": {"status": status, "limit": limit},
            "agent_info": "Requests processed by LangChain agent with database access"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/request/{request_id}")
async def get_request_details(
    request_id: int,
    supervision_service: SupervisionService = Depends(get_supervision_service)
):
    """Get detailed request info with agent decision analysis"""
    try:
        details = await supervision_service.get_request_details(request_id)
        
        # Enhance with agent analysis
        validation_checks = details.get("validation_results", {})
        
        enhanced_details = details.copy()
        enhanced_details["agent_analysis"] = {
            "processed_by_agent": validation_checks.get("processed_by") == "langchain_agent",
            "agent_success": validation_checks.get("agent_success", False),
            "business_analysis": validation_checks.get("business_analysis", ""),
            "model_used": validation_checks.get("model_used", "unknown"),
            "confidence_percentage": details["request"].get("confidence_score", 0) * 100 if details["request"].get("confidence_score") else 0
        }
        
        return enhanced_details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/request/{request_id}/reprocess-agent")
async def reprocess_with_agent(
    request_id: int,
    additional_context: str = "",
    reviewer_name: str = "supervisor",
    discount_service: DiscountService = Depends(get_discount_service)
):
    """
    Reprocess request with LangChain agent for second opinion
    """
    try:
        from app.models.chat import AgentReprocessRequest
        
        reprocess_request = AgentReprocessRequest(
            additional_context=additional_context,
            reviewer_name=reviewer_name
        )
        
        result = await discount_service.reprocess_with_agent(
            request_id=request_id,
            additional_context=reprocess_request.additional_context
        )
        
        return {
            "reprocessing_result": result,
            "message": "Agent has reprocessed the request. Compare both decisions.",
            "reviewer": reviewer_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/request/{request_id}/email")
async def update_email_draft(
    request_id: int,
    update_request: EmailUpdateRequest,
    supervision_service: SupervisionService = Depends(get_supervision_service)
):
    """Update email draft (now AI-generated by LangChain agent)"""
    try:
        result = await supervision_service.update_email_draft(
            request_id=request_id,
            new_email_content=update_request.email_content,
            reviewer_name=update_request.reviewer_name,
            notes=update_request.notes
        )
        
        # Add note about agent generation
        result["agent_note"] = "Original email was generated by LangChain agent"
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/request/{request_id}/approve")
async def approve_and_send(
    request_id: int,
    approval_request: ApprovalRequest,
    supervision_service: SupervisionService = Depends(get_supervision_service)
):
    """Final approval with one-click sending"""
    try:
        result = await supervision_service.approve_and_send_email(
            request_id=request_id,
            reviewer_name=approval_request.reviewer_name,
            final_notes=approval_request.final_notes
        )
        
        if result["success"]:
            result["workflow"] = "langchain_agent -> human_review -> email_sent"
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/request/{request_id}/reject")
async def reject_request(
    request_id: int,
    rejection_request: RejectionRequest,
    supervision_service: SupervisionService = Depends(get_supervision_service)
):
    """Human override rejection"""
    try:
        result = await supervision_service.reject_request(
            request_id=request_id,
            reviewer_name=rejection_request.reviewer_name,
            rejection_reason=rejection_request.rejection_reason
        )
        
        result["workflow"] = "langchain_agent -> human_override -> rejected"
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_supervision_stats(
    supervision_service: SupervisionService = Depends(get_supervision_service),
    discount_service: DiscountService = Depends(get_discount_service)
):
    """Enhanced stats with agent performance"""
    try:
        supervision_stats = await supervision_service.get_supervision_stats()
        agent_stats = await discount_service.get_agent_stats()
        
        return {
            "supervision": supervision_stats,
            "agent_performance": agent_stats,
            "combined_metrics": {
                "total_automation_rate": round(agent_stats["agent_success_rate"], 1),
                "human_intervention_needed": supervision_stats["pending_reviews"],
                "system_efficiency": "LangChain Agent + Human Supervision"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
async def export_requests_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Export with agent decision data"""
    return {
        "message": "CSV export with LangChain agent data coming soon",
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "status": status
        },
        "includes": ["agent_decisions", "confidence_scores", "business_analysis"]
    } 