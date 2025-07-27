"""
Simple Discount Service
Replaces LLM-based decision making with deterministic logic + template emails
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fuzzywuzzy import fuzz

from app.models.database import User, Show, DiscountRequest
from app.services.template_email_service import TemplateEmailService
from app.services.supervision_queue_service import SupervisionQueueService


class SimpleDiscountService:
    """
    🚀 SIMPLE & RELIABLE DISCOUNT PROCESSING
    
    Architecture:
    1. 🔒 PreFilter: User validations (exists, payments, subscription, duplicates)
    2. 🔍 Show Matching: Simple fuzzy matching (no LLM)
    3. 📧 Template Emails: Fixed templates with real data
    4. 👥 Supervision Queue: Human review
    
    Benefits:
    - ⚡ Super fast (< 1 second)
    - 🎯 100% reliable
    - 🚫 No hallucinations
    - 📝 Predictable
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.email_service = TemplateEmailService(db_session)
        self.supervision_queue = SupervisionQueueService(db_session)
    
    async def process_discount_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 Main processing flow - Simple and deterministic
        """
        start_time = time.time()
        
        try:
            # 1. 🔒 PreFilter: User validations
            prefilter_result = self._run_prefilter_validations(request_data)
            if prefilter_result["should_reject"]:
                return await self._handle_prefilter_rejection(request_data, prefilter_result, start_time)
            
            # 2. 🔍 Show matching: Simple fuzzy matching
            show_match_result = self._find_matching_shows(request_data["show_description"])
            
            if show_match_result["match_type"] == "single_match":
                return await self._handle_approval(request_data, show_match_result["show"], prefilter_result["user"], start_time)
            elif show_match_result["match_type"] == "multiple_matches":
                return await self._handle_clarification(request_data, show_match_result["shows"], start_time)
            else:  # no_match
                return await self._handle_no_show_found(request_data, start_time)
        
        except Exception as e:
            return await self._handle_error(request_data, str(e), start_time)
    
    def _run_prefilter_validations(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔒 PreFilter: Fast user-centric validations
        """
        user_email = request_data["user_email"]
        user_name = request_data["user_name"]
        
        # 1. Check if user exists
        user = self.db.query(User).filter(User.email == user_email).first()
        if not user:
            return {
                "should_reject": True,
                "reason_code": "user_not_found",
                "user": None
            }
        
        # 2. Check subscription status
        if not user.subscription_active:
            return {
                "should_reject": True,
                "reason_code": "subscription_inactive",
                "user": user
            }
        
        # 3. Check payment status
        if not user.monthly_fee_current:
            return {
                "should_reject": True,
                "reason_code": "payment_overdue",
                "user": user
            }
        
        # 4. Check for recent duplicate requests (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_request = self.db.query(DiscountRequest).filter(
            DiscountRequest.user_id == user.id,
            DiscountRequest.request_date > recent_cutoff
        ).first()
        
        if recent_request:
            return {
                "should_reject": True,
                "reason_code": "duplicate_request",
                "user": user
            }
        
        # ✅ All validations passed
        return {
            "should_reject": False,
            "user": user
        }
    
    def _find_matching_shows(self, show_description: str) -> Dict[str, Any]:
        """
        🔍 Simple fuzzy matching for shows (no LLM needed)
        """
        # Get all active shows with available discounts
        all_shows = self.db.query(Show).filter(Show.active == True).all()
        available_shows = [
            show for show in all_shows 
            if show.get_remaining_discounts(self.db) > 0
        ]
        
        if not available_shows:
            return {"match_type": "no_match", "shows": []}
        
        # Calculate similarity scores
        matches = []
        for show in available_shows:
            # Create searchable text combining title, artist, venue
            searchable_text = f"{show.title} {show.artist} {show.venue}".lower()
            description_lower = show_description.lower()
            
            # Calculate fuzzy similarity
            similarity = fuzz.partial_ratio(description_lower, searchable_text)
            
            if similarity >= 70:  # Threshold for match
                matches.append({
                    "show": show,
                    "similarity": similarity
                })
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        
        if len(matches) == 0:
            return {"match_type": "no_match", "shows": []}
        elif len(matches) == 1:
            return {"match_type": "single_match", "show": matches[0]["show"]}
        else:
            # Check if top match is significantly better than others
            top_score = matches[0]["similarity"]
            second_score = matches[1]["similarity"] if len(matches) > 1 else 0
            
            if top_score >= 90 and (top_score - second_score) >= 15:
                # Clear winner
                return {"match_type": "single_match", "show": matches[0]["show"]}
            else:
                # Multiple good matches, need clarification
                return {"match_type": "multiple_matches", "shows": [m["show"] for m in matches[:5]]}
    
    async def _handle_prefilter_rejection(self, request_data: Dict[str, Any], prefilter_result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """
        ❌ Handle PreFilter rejections with template emails
        """
        processing_time = time.time() - start_time
        
        # Generate rejection email
        email_data = self.email_service.generate_rejection_email(
            user_name=request_data["user_name"],
            user_email=request_data["user_email"],
            reason_code=prefilter_result["reason_code"],
            show_info=request_data["show_description"]
        )
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data["request_id"],
            "user_email": request_data["user_email"],
            "user_name": request_data["user_name"],
            "show_description": request_data["show_description"],
            "decision_source": "prefilter_template",
            "processing_time": processing_time,
            **email_data
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        
        return {
            "decision": "rejected",
            "reasoning": email_data["reasoning"],
            "queue_id": queue_item.id,
            "status": "queued_for_supervision",
            "processing_time": processing_time
        }
    
    async def _handle_approval(self, request_data: Dict[str, Any], show: Show, user: User, start_time: float) -> Dict[str, Any]:
        """
        ✅ Handle approval with template email
        """
        processing_time = time.time() - start_time
        
        # Double-check show still has discounts
        remaining = show.get_remaining_discounts(self.db)
        if remaining <= 0:
            return await self._handle_no_discounts_available(request_data, show, start_time)
        
        # Generate approval email
        email_data = self.email_service.generate_approval_email(user, show)
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data["request_id"],
            "user_email": request_data["user_email"],
            "user_name": request_data["user_name"],
            "show_description": request_data["show_description"],
            "decision_source": "template_approval",
            "processing_time": processing_time,
            **email_data
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        
        return {
            "decision": "approved",
            "reasoning": email_data["reasoning"],
            "discount_percentage": email_data["discount_percentage"],
            "queue_id": queue_item.id,
            "status": "queued_for_supervision",
            "processing_time": processing_time
        }
    
    async def _handle_clarification(self, request_data: Dict[str, Any], shows: List[Show], start_time: float) -> Dict[str, Any]:
        """
        ❓ Handle multiple matches with clarification email
        """
        processing_time = time.time() - start_time
        
        # Generate clarification email
        email_data = self.email_service.generate_clarification_email(
            user_name=request_data["user_name"],
            user_email=request_data["user_email"],
            available_shows=shows,
            user_query=request_data["show_description"]
        )
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data["request_id"],
            "user_email": request_data["user_email"],
            "user_name": request_data["user_name"],
            "show_description": request_data["show_description"],
            "decision_source": "template_clarification",
            "processing_time": processing_time,
            **email_data
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        
        return {
            "decision": "needs_clarification",
            "reasoning": email_data["reasoning"],
            "queue_id": queue_item.id,
            "status": "queued_for_supervision",
            "processing_time": processing_time
        }
    
    async def _handle_no_show_found(self, request_data: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """
        🔍 Handle when no matching shows are found
        """
        processing_time = time.time() - start_time
        
        # Generate rejection email for no show found
        email_data = self.email_service.generate_rejection_email(
            user_name=request_data["user_name"],
            user_email=request_data["user_email"],
            reason_code="no_discounts_available",
            show_info=request_data["show_description"] + " (No se encontraron shows coincidentes)"
        )
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data["request_id"],
            "user_email": request_data["user_email"],
            "user_name": request_data["user_name"],
            "show_description": request_data["show_description"],
            "decision_source": "template_no_match",
            "processing_time": processing_time,
            **email_data
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        
        return {
            "decision": "rejected",
            "reasoning": "No se encontraron shows que coincidan con la búsqueda",
            "queue_id": queue_item.id,
            "status": "queued_for_supervision",
            "processing_time": processing_time
        }
    
    async def _handle_no_discounts_available(self, request_data: Dict[str, Any], show: Show, start_time: float) -> Dict[str, Any]:
        """
        🎫 Handle when show exists but no discounts available
        """
        processing_time = time.time() - start_time
        
        show_info = f"{show.title} - {show.artist} en {show.venue}"
        
        # Generate rejection email
        email_data = self.email_service.generate_rejection_email(
            user_name=request_data["user_name"],
            user_email=request_data["user_email"],
            reason_code="no_discounts_available",
            show_info=show_info
        )
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data["request_id"],
            "user_email": request_data["user_email"],
            "user_name": request_data["user_name"],
            "show_description": request_data["show_description"],
            "decision_source": "template_no_discounts",
            "processing_time": processing_time,
            "show_id": show.id,
            **email_data
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        
        return {
            "decision": "rejected",
            "reasoning": f"Show encontrado pero sin descuentos disponibles: {show_info}",
            "queue_id": queue_item.id,
            "status": "queued_for_supervision",
            "processing_time": processing_time
        }
    
    async def _handle_error(self, request_data: Dict[str, Any], error_msg: str, start_time: float) -> Dict[str, Any]:
        """
        🚨 Handle unexpected errors
        """
        processing_time = time.time() - start_time
        
        return {
            "decision": "error",
            "reasoning": f"Error técnico: {error_msg}",
            "queue_id": 0,  # Use 0 instead of None for Pydantic validation
            "status": "error",
            "processing_time": processing_time
        } 