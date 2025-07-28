"""
Discount Decision Service - New Architecture
Integrates PreFilter (deterministic validation) + IntelligentMatcher (LLM-powered) 
"""

import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.discount_prefilter import DiscountPreFilter, PreFilterResult
from app.services.intelligent_matcher import IntelligentShowMatcher, MatchingResult
from app.services.template_email_service import TemplateEmailService
from app.services.decision_logger import DecisionLogger
from app.services.supervision_queue_service import SupervisionQueueService


logger = logging.getLogger(__name__)


class DiscountDecisionService:
    """
    🎯 MAIN DISCOUNT DECISION SERVICE - New Architecture
    
    Architecture:
    1. PreFilter: Fast deterministic business rule validation (80% of cases)
    2. IntelligentMatcher: LLM-powered fuzzy matching + email generation (20% of cases)
    
    Benefits:
    - Fast rejections (<1 second for invalid requests)  
    - Intelligent matching only for complex cases
    - Clean separation of deterministic vs AI logic
    - Easy to debug and maintain
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.prefilter = DiscountPreFilter(db_session)
        self.intelligent_matcher = IntelligentShowMatcher(db_session)  # Pass DB session
        self.email_engine = TemplateEmailService(db_session)
        self.decision_logger = DecisionLogger()
        self.supervision_queue = SupervisionQueueService(db_session)
    
    async def process_discount_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 Main processing method with new architecture
        
        Flow:
        1. PreFilter validates all business rules deterministically
        2. If rejected → return immediate rejection with simple email
        3. If approved → pass clean data to IntelligentMatcher for fuzzy matching + email
        """
        request_id = request_data.get("request_id", "unknown")
        start_time = datetime.now()
        
        logger.info(f"🎯 Processing request {request_id} with new architecture")
        
        try:
            # PHASE 1: DETERMINISTIC PRE-FILTER VALIDATION
            logger.info(f"🔒 Phase 1: PreFilter validation")
            prefilter_result = self.prefilter.validate_request(request_data)
            
            if prefilter_result.rejected:
                # ❌ IMMEDIATE REJECTION - No LLM needed
                rejection_response = self._create_prefilter_rejection_response(
                    prefilter_result, request_data, start_time
                )
                logger.info(f"❌ Request {request_id} rejected by PreFilter: {prefilter_result.reason}")
                return rejection_response
            
            # PHASE 2: INTELLIGENT MATCHING + EMAIL GENERATION  
            logger.info(f"🤖 Phase 2: LLM intelligent matching and show analysis")
            matching_result = await self.intelligent_matcher.process_validated_request(prefilter_result)
            
            if matching_result.status == "approved":
                # ✅ APPROVAL - Generate final response
                approval_response = self._create_intelligent_approval_response(
                    matching_result, prefilter_result, request_data, start_time
                )
                logger.info(f"✅ Request {request_id} approved: {matching_result.show_selected['title']}")
                return approval_response
                
            elif matching_result.status == "needs_clarification":
                # 🤔 CLARIFICATION NEEDED - Generate clarification response
                clarification_response = self._create_clarification_response(
                    matching_result, prefilter_result, request_data, start_time
                )
                logger.info(f"🤔 Request {request_id} needs clarification")
                return clarification_response
            
        except Exception as e:
            # 🚨 ERROR HANDLING
            error_response = self._create_error_response(request_data, str(e), start_time)
            logger.error(f"🚨 Error processing request {request_id}: {str(e)}")
            return error_response
    
    def _create_prefilter_rejection_response(self, prefilter_result: PreFilterResult, 
                                           request_data: Dict[str, Any], 
                                           start_time: datetime) -> Dict[str, Any]:
        """Create response for PreFilter rejections (fast, deterministic)"""
        
        # Generate simple rejection email
        rejection_email = self._generate_simple_rejection_email(
            request_data.get("user_name", "Usuario"),
            prefilter_result.reason
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "user_name": request_data.get("user_name", "Usuario"),
            "show_description": request_data.get("show_description"),
            "decision": "rejected",
            "decision_source": "prefilter_template",
            "show_id": None,
            "email_content": rejection_email,
            "confidence": 1.0,
            "reasoning": prefilter_result.reason,
            "processing_time": processing_time
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        
        # Log decision
        decision_log = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "show_description": request_data.get("show_description"),
            "decision_method": "prefilter_deterministic",
            "final_decision": "REJECTED",
            "rejection_reason": prefilter_result.reason,
            "processing_time_seconds": processing_time,
            "llm_used": False,
            "candidate_shows_found": 0,
            "timestamp": datetime.now().isoformat(),
            "queue_id": queue_item.id
        }
        self.decision_logger.log_decision(decision_log)
        
        return {
            "success": True,
            "decision": "rejected",
            "show_id": None,
            "discount_percentage": 0,
            "confidence": 1.0,  # High confidence for deterministic rejections
            "reasoning": prefilter_result.reason,
            "email_content": rejection_email,
            "business_analysis": f"PreFilter rejection: {prefilter_result.reason}",
            "processing_time": processing_time,
            "validation_method": "deterministic_prefilter",
            "queue_id": queue_item.id,
            "status": "queued_for_supervision"
        }
    
    def _create_intelligent_approval_response(self, matching_result: MatchingResult,
                                            prefilter_result: PreFilterResult,
                                            request_data: Dict[str, Any],
                                            start_time: datetime) -> Dict[str, Any]:
        """Create response for intelligent matcher approvals"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        selected_show = matching_result.show_selected
        
        # Log decision
        decision_log = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "show_description": request_data.get("show_description"),
            "decision_method": "intelligent_matcher",
            "final_decision": "APPROVED",
            "show_matched": {
                "id": selected_show["id"],
                "title": selected_show["title"],
                "artist": selected_show["artist"],
                "venue": selected_show["venue"]
            },
            "llm_reasoning": matching_result.reasoning,
            "processing_time_seconds": processing_time,
            "llm_used": matching_result.llm_used,
            "candidate_shows_found": len(prefilter_result.candidate_shows),
            "confidence_score": matching_result.confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "user_name": prefilter_result.user_data.get("name", "Usuario"),
            "show_description": request_data.get("show_description"),
            "decision": "approved",
            "decision_source": "llm_generated",
            "show_id": selected_show["id"],
            "email_content": matching_result.email_content,
            "confidence": matching_result.confidence,
            "reasoning": matching_result.reasoning,
            "processing_time": processing_time
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        decision_log["queue_id"] = queue_item.id
        self.decision_logger.log_decision(decision_log)
        
        return {
            "success": True,
            "decision": "approved",
            "show_id": selected_show["id"],
            "discount_percentage": 15,  # Default discount
            "confidence": matching_result.confidence,
            "reasoning": matching_result.reasoning,
            "email_content": matching_result.email_content,
            "business_analysis": f"Intelligent match: {selected_show['title']} selected from available shows",
            "processing_time": processing_time,
            "validation_method": "prefilter_plus_intelligent_matching",
            "queue_id": queue_item.id,
            "status": "queued_for_supervision"
        }
    
    def _create_error_response(self, request_data: Dict[str, Any], 
                             error_message: str, start_time: datetime) -> Dict[str, Any]:
        """Create response for system errors"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Log error
        error_log = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "decision_method": "error_handler",
            "final_decision": "REJECTED",
            "error_message": error_message,
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        self.decision_logger.log_decision(error_log)
        
        return {
            "success": False,
            "decision": "rejected",
            "show_id": None,
            "discount_percentage": 0,
            "confidence": 1.0,
            "reasoning": f"Error técnico en el procesamiento: {error_message}",
            "email_content": "Error procesando solicitud. Contacte soporte.",
            "business_analysis": f"System error: {error_message}",
            "processing_time": processing_time,
            "error": error_message
        }
    
    def _create_clarification_response(self, matching_result: MatchingResult,
                                     prefilter_result: PreFilterResult,
                                     request_data: Dict[str, Any],
                                     start_time: datetime) -> Dict[str, Any]:
        """Create response for requests that need clarification"""
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Log decision
        decision_log = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "show_description": request_data.get("show_description"),
            "decision_method": "intelligent_matcher_clarification",
            "final_decision": "NEEDS_CLARIFICATION",
            "llm_reasoning": matching_result.reasoning,
            "processing_time_seconds": processing_time,
            "llm_used": matching_result.llm_used,
            "candidate_shows_found": 0,  # No final show selected
            "confidence_score": matching_result.confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to supervision queue
        queue_data = {
            "request_id": request_data.get("request_id"),
            "user_email": request_data.get("user_email"),
            "user_name": prefilter_result.user_data.get("name", "Usuario"),
            "show_description": request_data.get("show_description"),
            "decision": "needs_clarification",
            "decision_source": "llm_generated",
            "show_id": None,
            "email_content": matching_result.email_content,
            "confidence": matching_result.confidence,
            "reasoning": matching_result.reasoning,
            "processing_time": processing_time
        }
        
        queue_item = self.supervision_queue.add_to_queue(queue_data)
        decision_log["queue_id"] = queue_item.id
        self.decision_logger.log_decision(decision_log)
        
        return {
            "success": True,
            "decision": "needs_clarification",
            "show_id": None,
            "discount_percentage": 0,
            "confidence": matching_result.confidence,
            "reasoning": matching_result.reasoning,
            "email_content": matching_result.email_content,
            "business_analysis": f"Clarification needed: {matching_result.reasoning}",
            "processing_time": processing_time,
            "validation_method": "prefilter_plus_intelligent_matching",
            "requires_user_response": True,
            "queue_id": queue_item.id,
            "status": "queued_for_supervision"
        }
    
    def _generate_simple_rejection_email(self, user_name: str, reason: str) -> str:
        """Generate simple rejection email for PreFilter rejections"""
        
        # Map technical reasons to user-friendly messages
        user_friendly_reasons = {
            "no está registrado": "su email no se encuentra en nuestro sistema de suscriptores",
            "cuotas mensuales pendientes": "tiene pagos pendientes que deben regularizarse",
            "suscripción no está activa": "su suscripción necesita ser activada",
            "no encontramos shows": "no hay shows disponibles que coincidan con su búsqueda",
            "ya tiene una solicitud": "ya solicitó un descuento para este show anteriormente"
        }
        
        friendly_reason = reason
        for key, friendly in user_friendly_reasons.items():
            if key in reason.lower():
                friendly_reason = friendly
                break
        
        return f"""Estimado/a {user_name},

Hemos recibido su solicitud de descuento, pero lamentablemente no podemos procesarla en este momento porque {friendly_reason}.

Por favor:
• Verifique su información de cuenta
• Asegúrese de que sus pagos estén al día
• Contacte nuestro soporte si necesita asistencia

Puede responder a este email para obtener más información.

Saludos cordiales,
Equipo IndieHOY"""

    async def test_system_health(self) -> Dict[str, Any]:
        """Test both PreFilter and IntelligentMatcher components"""
        health_status = {
            "prefilter": {"status": "ok", "message": "PreFilter loaded successfully"},
            "intelligent_matcher": await self.intelligent_matcher.test_llm_connection(),
            "overall_status": "healthy"
        }
        
        if not health_status["intelligent_matcher"]["success"]:
            health_status["overall_status"] = "degraded"
            health_status["note"] = "LLM unavailable - will use fallback matching"
        
        return health_status 