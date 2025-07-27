"""
Supervision Service
Handles human review and oversight of discount decisions
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database import DiscountRequest, User, Show
from app.services.email_service import EmailService


class SupervisionService:
    """
    Service for human supervision of discount decisions
    Manages the review landing page and approval workflow
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
    
    async def get_pending_reviews(
        self, 
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all discount requests pending human review
        
        This feeds the supervision landing page
        """
        
        query = self.db.query(DiscountRequest).join(User).join(Show)
        
        # Filter by status if provided
        if status_filter:
            query = query.filter(DiscountRequest.status == status_filter)
        else:
            # Default: show processed but not yet reviewed requests
            query = query.filter(
                DiscountRequest.processed_at.isnot(None),
                DiscountRequest.human_reviewed == False
            )
        
        # Order by priority: approved first, then by creation date
        query = query.order_by(
            DiscountRequest.approved.desc(),
            DiscountRequest.created_at.desc()
        ).limit(limit)
        
        requests = query.all()
        
        # Format for frontend
        pending_reviews = []
        for req in requests:
            pending_reviews.append({
                "id": req.id,
                "user_name": req.user.name,
                "user_email": req.user.email,
                "show_title": req.show.title,
                "show_artist": req.show.artist,
                "show_date": req.show.date,
                "reason": req.reason,
                "approved": req.approved,
                "discount_percentage": req.final_discount_percentage,
                "llm_reasoning": req.llm_reasoning,
                "confidence_score": req.confidence_score,
                "email_draft": req.email_draft,
                "created_at": req.created_at,
                "processed_at": req.processed_at,
                "validation_checks": req.validation_checks,
                # UI helpers
                "priority": "high" if req.approved else "normal",
                "estimated_savings": self._calculate_savings(req.show.base_price, req.final_discount_percentage) if req.final_discount_percentage else 0
            })
        
        return pending_reviews
    
    async def get_request_details(self, request_id: int) -> Dict[str, Any]:
        """Get detailed information for a specific request"""
        
        request = self.db.query(DiscountRequest).join(User).join(Show).filter(
            DiscountRequest.id == request_id
        ).first()
        
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        return {
            "request": {
                "id": request.id,
                "status": request.status,
                "approved": request.approved,
                "discount_percentage": request.final_discount_percentage,
                "reason": request.reason,
                "llm_reasoning": request.llm_reasoning,
                "confidence_score": request.confidence_score,
                "email_draft": request.email_draft,
                "human_reviewed": request.human_reviewed,
                "human_notes": request.human_notes,
                "created_at": request.created_at,
                "processed_at": request.processed_at
            },
            "user": {
                "id": request.user.id,
                "name": request.user.name,
                "email": request.user.email,
                "subscription_active": request.user.subscription_active,
                "monthly_fee_current": request.user.monthly_fee_current,
                "total_discounts_used": request.user.total_discounts_used,
                "monthly_discount_count": request.user.monthly_discount_count
            },
            "show": {
                "id": request.show.id,
                "title": request.show.title,
                "artist": request.show.artist,
                "venue": request.show.venue,
                "date": request.show.date,
                "base_price": request.show.base_price,
                "max_discount_percentage": request.show.max_discount_percentage
            },
            "validation_results": request.validation_checks,
            "potential_savings": self._calculate_savings(request.show.base_price, request.final_discount_percentage) if request.final_discount_percentage else 0
        }
    
    async def update_email_draft(
        self, 
        request_id: int, 
        new_email_content: str,
        reviewer_name: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Human reviewer updates the email draft
        """
        
        request = self.db.query(DiscountRequest).filter(
            DiscountRequest.id == request_id
        ).first()
        
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        # Store original email for comparison
        original_email = request.email_draft
        
        # Update the request
        request.human_modified_email = new_email_content
        request.human_reviewer = reviewer_name
        request.human_notes = notes
        request.reviewed_at = datetime.now()
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Email draft updated successfully",
            "request_id": request_id,
            "reviewer": reviewer_name,
            "changes_made": original_email != new_email_content
        }
    
    async def approve_and_send_email(
        self, 
        request_id: int, 
        reviewer_name: str,
        final_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Final approval: mark as reviewed and send email to user
        """
        
        request = self.db.query(DiscountRequest).join(User).filter(
            DiscountRequest.id == request_id
        ).first()
        
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        if request.email_sent:
            return {
                "success": False,
                "error": "Email already sent for this request"
            }
        
        # Determine final email content (human modified or original)
        email_content = request.human_modified_email or request.email_draft
        
        if not email_content:
            return {
                "success": False,
                "error": "No email content available"
            }
        
        # Send email
        email_result = await self.email_service.send_discount_email(
            to_email=request.user.email,
            to_name=request.user.name,
            subject=self._generate_email_subject(request.approved, request.final_discount_percentage),
            email_content=email_content,
            request_id=request.id,
            is_approval=request.approved,
            discount_percentage=request.final_discount_percentage
        )
        
        if email_result["sent"]:
            # Update request status
            request.email_sent = True
            request.email_sent_at = datetime.now()
            request.human_reviewed = True
            request.human_reviewer = reviewer_name
            request.human_notes = final_notes
            request.status = "sent"
            
            self.db.commit()
            
            # Create history record
            self._create_history_record(request, "sent", reviewer_name)
            
            # Update user statistics if approved
            if request.approved:
                self._update_user_stats(request.user.id)
            
            return {
                "success": True,
                "message": "Email sent successfully",
                "request_id": request_id,
                "email_sent_to": request.user.email,
                "reviewer": reviewer_name
            }
        else:
            return {
                "success": False,
                "error": f"Failed to send email: {email_result.get('error', 'Unknown error')}"
            }
    
    async def reject_request(
        self, 
        request_id: int, 
        reviewer_name: str,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """
        Human reviewer rejects the request (override agent decision)
        """
        
        request = self.db.query(DiscountRequest).filter(
            DiscountRequest.id == request_id
        ).first()
        
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        # Update request to rejected
        original_approved = request.approved
        request.approved = False
        request.final_discount_percentage = 0
        request.status = "rejected"
        request.human_reviewed = True
        request.human_reviewer = reviewer_name
        request.human_notes = f"Human override: {rejection_reason}"
        request.reviewed_at = datetime.now()
        
        self.db.commit()
        
        # Create history record
        self._create_history_record(request, "human_rejected", reviewer_name)
        
        return {
            "success": True,
            "message": "Request rejected by human reviewer",
            "request_id": request_id,
            "was_agent_approved": original_approved,
            "reviewer": reviewer_name
        }
    
    async def get_supervision_stats(self) -> Dict[str, Any]:
        """Get statistics for supervision dashboard"""
        
        # Pending reviews
        pending_count = self.db.query(DiscountRequest).filter(
            DiscountRequest.processed_at.isnot(None),
            DiscountRequest.human_reviewed == False
        ).count()
        
        # Today's activity
        today = datetime.now().date()
        today_processed = self.db.query(DiscountRequest).filter(
            DiscountRequest.processed_at >= today
        ).count()
        
        today_sent = self.db.query(DiscountRequest).filter(
            DiscountRequest.email_sent_at >= today
        ).count()
        
        # Approval rates
        total_processed = self.db.query(DiscountRequest).filter(
            DiscountRequest.processed_at.isnot(None)
        ).count()
        
        agent_approved = self.db.query(DiscountRequest).filter(
            DiscountRequest.approved == True,
            DiscountRequest.processed_at.isnot(None)
        ).count()
        
        approval_rate = (agent_approved / total_processed * 100) if total_processed > 0 else 0
        
        return {
            "pending_reviews": pending_count,
            "today_processed": today_processed,
            "today_sent": today_sent,
            "total_processed": total_processed,
            "agent_approval_rate": round(approval_rate, 1),
            "average_confidence": self._get_average_confidence(),
            "high_priority_pending": self.db.query(DiscountRequest).filter(
                DiscountRequest.approved == True,
                DiscountRequest.human_reviewed == False
            ).count()
        }
    
    def _calculate_savings(self, base_price: float, discount_percentage: Optional[float]) -> float:
        """Calculate monetary savings from discount"""
        if not discount_percentage:
            return 0.0
        return base_price * (discount_percentage / 100)
    
    def _generate_email_subject(self, approved: bool, discount_percentage: Optional[float]) -> str:
        """Generate email subject line"""
        if approved and discount_percentage:
            return f"🎉 ¡Descuento aprobado! {discount_percentage}% para tu show"
        else:
            return "Respuesta a tu solicitud de descuento"
    
    def _create_history_record(self, request: DiscountRequest, action: str, actor: str):
        """Create historical record"""
        
        history = DiscountHistory(
            discount_request_id=request.id,
            user_email=request.user.email,
            show_title=request.show.title,
            discount_percentage=request.final_discount_percentage or 0,
            original_price=request.show.base_price,
            final_price=request.show.base_price * (1 - (request.final_discount_percentage or 0) / 100),
            action=action,
            actor=actor
        )
        
        self.db.add(history)
        self.db.commit()
    
    def _update_user_stats(self, user_id: int):
        """Update user discount statistics"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.total_discounts_used += 1
            user.monthly_discount_count += 1  # This would reset monthly in a real system
            self.db.commit()
    
    def _get_average_confidence(self) -> float:
        """Get average confidence score of recent agent decisions"""
        
        recent_requests = self.db.query(DiscountRequest).filter(
            DiscountRequest.confidence_score.isnot(None),
            DiscountRequest.processed_at.isnot(None)
        ).order_by(DiscountRequest.processed_at.desc()).limit(100).all()
        
        if not recent_requests:
            return 0.0
        
        avg_confidence = sum(req.confidence_score for req in recent_requests) / len(recent_requests)
        return round(avg_confidence * 100, 1)  # Convert to percentage 