"""
Discount Service (Updated for LangChain Agent)
Main business logic using LangChain agent for decision making
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.database import User, Show, DiscountRequest
from app.models.forms import DiscountRequest as DiscountRequestSchema, DiscountResponse
from app.services.langchain_agent_service import LangChainAgentService
from app.services.email_service import EmailService
from app.core.config import settings


class DiscountService:
    """
    Main service for discount request processing using LangChain Agent
    The agent now handles validation, decision making, and email generation
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.agent_service = LangChainAgentService(db)
        self.email_service = EmailService()
    
    async def process_request(self, request: DiscountRequestSchema) -> DiscountResponse:
        """
        Main method: Process discount request using LangChain Agent
        
        New Flow:
        1. Create database record
        2. LangChain Agent makes decision (includes validation, reasoning, email generation)
        3. Store results for human review
        4. Return response
        """
        
        # 1. Validate user exists (registered users only)
        user_id = await self._get_existing_user(request.user_email)
        if not user_id:
            raise ValueError(f"Email {request.user_email} is not registered. Please register first.")
        
        # 2. Create database record (show will be determined by LLM)
        db_request = DiscountRequest(
            user_id=user_id,
            show_id=None,  # Will be determined by LLM from show_description
            other_data={
                "show_description": request.show_description,
                "user_name_provided": request.user_name
            }
        )
        self.db.add(db_request)
        self.db.commit()
        self.db.refresh(db_request)
        
        # 3. LangChain Agent processes the request
        agent_result = await self.agent_service.process_discount_request({
            "request_id": db_request.id,
            "user_email": request.user_email,
            "user_name": request.user_name,
            "show_description": request.show_description
        })
        
        # 4. Update database with agent decision
        if agent_result["success"]:
            db_request.approved = (agent_result["decision"] == "approved")
            db_request.show_id = agent_result.get("show_id")  # Now set by agent
            
            # Store agent results in other_data
            db_request.other_data.update({
                "final_discount_percentage": agent_result.get("discount_percentage", 0),
                "llm_reasoning": agent_result["reasoning"],
                "confidence_score": agent_result["confidence"],
                "email_draft": agent_result["email_content"],
                "agent_decision_status": "processed",
                "agent_analysis": {
                    "agent_decision": agent_result["decision"],
                    "business_analysis": agent_result.get("business_analysis", ""),
                    "agent_success": True,
                    "processed_by": "langchain_agent",
                    "model_used": settings.OLLAMA_MODEL
                }
            })
            db_request.agent_approval_date = datetime.now()
        else:
            db_request.approved = False
            db_request.other_data.update({
                "llm_reasoning": agent_result.get("reasoning", "Agent processing failed"),
                "confidence_score": agent_result.get("confidence", 0.0),
                "email_draft": agent_result.get("email_content", "Error generating email"),
                "agent_decision_status": "failed",
                "agent_analysis": {
                    "agent_decision": "rejected",
                    "business_analysis": agent_result.get("business_analysis", "Agent failure"),
                    "agent_success": False,
                    "processed_by": "langchain_agent",
                    "model_used": settings.OLLAMA_MODEL,
                    "error": agent_result.get("error", "Unknown error")
                }
            })
            db_request.agent_approval_date = datetime.now()

        self.db.commit()
        self.db.refresh(db_request)
        
        # 5. Return response for frontend/chatbot
        return DiscountResponse(
            approved=db_request.approved,
            discount_percentage=db_request.other_data.get("final_discount_percentage"),
            reason=db_request.other_data.get("llm_reasoning", "Solicitud procesada."),
            request_id=db_request.id,
            expiry_date=datetime.now() + timedelta(days=7),
            terms=["Descuento válido por 7 días", "Sujeto a disponibilidad", "Un descuento por persona"]
        )

    async def get_status(self, request_id: str) -> Dict[str, Any]:
        """Get status of discount request"""
        request = self.db.query(DiscountRequest).filter(
            DiscountRequest.id == int(request_id)
        ).first()
        
        if not request:
            raise ValueError("Request not found")
        
        return {
            "id": request.id,
            "approved": request.approved,
            "human_approved": request.human_approved,
            "request_date": request.request_date,
            "agent_approval_date": request.agent_approval_date,
            "other_data": request.other_data
        }

    async def reprocess_with_agent(self, request_id: int, additional_context: str) -> Dict[str, Any]:
        """Reprocess a request with the LangChain agent"""
        db_request = self.db.query(DiscountRequest).filter(DiscountRequest.id == request_id).first()
        if not db_request:
            raise ValueError("Request not found")
        
        # Get original request data
        user = self.db.query(User).filter(User.id == db_request.user_id).first()
        
        # Reprocess with agent including additional context
        agent_result = await self.agent_service.process_discount_request({
            "request_id": request_id,
            "user_email": user.email,
            "user_name": user.name,
            "show_description": db_request.other_data.get("show_description", ""),
            "additional_context": additional_context
        })
        
        return {
            "request_id": request_id,
            "original_decision": db_request.approved,
            "new_agent_result": agent_result,
            "recommendation": "Review both decisions for final choice"
        }
    
    def _store_agent_decision(self, request_id: int, agent_result: Dict[str, Any]):
        """Store detailed agent decision for analytics (now in other_data field)"""
        # Agent analytics are now stored in the other_data JSON field
        # And also in the JSON log file via DecisionLogger
        pass
    
    async def _get_existing_user(self, email: str) -> Optional[int]:
        """Get existing registered user (no creation)"""
        user = self.db.query(User).filter(User.email == email).first()
        return user.id if user else None
    
    async def _get_show_id(self, show_identifier: str) -> int:
        """Get show ID from identifier"""
        try:
            show_id = int(show_identifier)
            show = self.db.query(Show).filter(Show.id == show_id).first()
            if show:
                return show.id
            raise ValueError(f"Show not found: {show_identifier}")
        except ValueError:
            raise ValueError(f"Invalid show ID format: {show_identifier}")
    
    async def get_agent_stats(self) -> Dict[str, Any]:
        """
        Get LangChain agent performance statistics
        """
        total_requests = self.db.query(DiscountRequest).count()
        approved_by_agent = self.db.query(DiscountRequest).filter(DiscountRequest.approved == True).count()
        rejected_by_agent = self.db.query(DiscountRequest).filter(DiscountRequest.approved == False).count()
        human_approved_count = self.db.query(DiscountRequest).filter(DiscountRequest.human_approved == True).count()
        
        # Calculate average confidence from other_data
        requests_with_confidence = self.db.query(DiscountRequest).filter(
            DiscountRequest.other_data.isnot(None)
        ).all()
        
        confidence_scores = []
        for req in requests_with_confidence:
            if req.other_data and isinstance(req.other_data, dict):
                confidence = req.other_data.get("confidence_score")
                if confidence is not None:
                    confidence_scores.append(float(confidence))
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            "total_requests": total_requests,
            "approved_by_agent": approved_by_agent,
            "rejected_by_agent": rejected_by_agent,
            "human_approved_count": human_approved_count,
            "average_confidence": round(avg_confidence, 2),
            "model_used": settings.OLLAMA_MODEL,
            "agent_version": "1.0_langchain_rag"
        } 