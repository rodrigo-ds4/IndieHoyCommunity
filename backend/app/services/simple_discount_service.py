"""
Simple Discount Service
Replaces LLM-based decision making with deterministic logic + template emails
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
# Ya no necesitamos fuzzywuzzy
# from fuzzywuzzy import fuzz

from app.models.database import User, Show, SupervisionQueue
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
        🎯 Flujo de procesamiento principal - Simplificado para usar show_id directamente.
        """
        start_time = time.time()
        
        try:
            # 1. 🔒 PreFilter: Validaciones de usuario
            prefilter_result = self._run_prefilter_validations(request_data)
            if prefilter_result["should_reject"]:
                # Agregamos show_info para el template de email
                request_data['show_info'] = f"Show ID: {request_data.get('show_id')}"
                return await self._handle_rejection(request_data, prefilter_result["reason_code"], start_time)
            
            # 2. 🎯 Búsqueda directa y validación del show por ID
            show_id = request_data.get("show_id")
            show = self.db.query(Show).get(show_id)

            # Validar si el show existe y está disponible
            if not show or not show.active:
                return await self._handle_rejection(request_data, "show_not_found", start_time)
            
            if show.get_remaining_discounts(self.db) <= 0:
                return await self._handle_no_discounts_available(request_data, show, start_time)

            # 3. ✅ Aprobación
            return await self._handle_approval(request_data, show, prefilter_result["user"], start_time)
        
        except Exception as e:
            return await self._handle_error(request_data, str(e), start_time)
    
    def _run_prefilter_validations(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔒 PreFilter: Validaciones rápidas centradas en el usuario.
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
        
        # 4. Check for duplicate requests CORRECTLY in the supervision queue.
        #    A duplicate is a request for the same show and user that has not been rejected.
        show_id = request_data.get("show_id")
        existing_request = self.db.query(SupervisionQueue).filter(
            SupervisionQueue.user_email == user_email,
            SupervisionQueue.show_id == show_id,
            SupervisionQueue.status.in_(['pending', 'approved', 'sent'])
        ).first()
        
        if existing_request:
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
    
    # ELIMINADO: Ya no necesitamos el método _find_matching_shows
    # ELIMINADO: Ya no necesitamos el método _handle_clarification
    # ELIMINADO: Ya no necesitamos el método _handle_no_show_found

    async def _handle_rejection(self, request_data: Dict[str, Any], reason_code: str, start_time: float) -> Dict[str, Any]:
        """
        ❌ Maneja rechazos genéricos con templates de email.
        """
        processing_time = time.time() - start_time
        
        show_id = request_data.get("show_id")
        show = self.db.query(Show).get(show_id) if show_id else None
        show_info = f"{show.title}" if show else f"Show ID {show_id}"

        email_data = self.email_service.generate_rejection_email(
            user_name=request_data["user_name"],
            user_email=request_data["user_email"],
            reason_code=reason_code,
            show_info=show_info
        )
        
        queue_data = {
            "request_id": request_data["request_id"],
            "user_email": request_data["user_email"],
            "user_name": request_data["user_name"],
            "show_description": show_info,
            "decision_source": "prefilter_rejection",
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
            show_info=request_data.get("show_info", "")
        )
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data["request_id"],
            "user_email": request_data["user_email"],
            "user_name": request_data["user_name"],
            "show_description": request_data.get("show_info", f"Show ID: {request_data.get('show_id')}"),
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
            "show_description": show.title,
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
            "show_description": show_info,
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