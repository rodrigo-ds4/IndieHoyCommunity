"""
Discount PreFilter Service
Handles all deterministic business rule validations before LLM processing
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from fuzzywuzzy import fuzz

from app.models.database import User, Show, DiscountRequest

logger = logging.getLogger(__name__)


@dataclass
class PreFilterResult:
    """Result of pre-filter validation"""
    approved: bool
    rejected: bool
    reason: str
    user_data: Optional[Dict[str, Any]] = None
    candidate_shows: Optional[List[Dict[str, Any]]] = None
    original_description: Optional[str] = None
    ready_for_llm: bool = False


class DiscountPreFilter:
    """
    🔒 PRE-FILTER: Deterministic business rule validation
    
    Handles all the "hard" business logic that doesn't require AI:
    - User exists and is valid
    - Payments are current
    - Subscription is active  
    - Shows have available discounts
    - No duplicate requests
    
    Only passes "clean" data to LLM for fuzzy matching + email generation
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def validate_request(self, request_data: Dict[str, Any]) -> PreFilterResult:
        """
        🎯 Main validation method - applies all business rules deterministically
        
        Returns:
        - PreFilterResult with approved=False if any validation fails
        - PreFilterResult with approved=True + clean data if all validations pass
        """
        user_email = request_data.get("user_email")
        show_description = request_data.get("show_description")
        
        # 1. ❌ VALIDATION: User must exist
        user_data = self._get_user_by_email(user_email)
        if not user_data:
            return PreFilterResult(
                approved=False,
                rejected=True,
                reason=f"El email {user_email} no está registrado en nuestro sistema"
            )
        
        # 2. ❌ VALIDATION: User must have current payments
        if not user_data.get("monthly_fee_current"):
            return PreFilterResult(
                approved=False,
                rejected=True,
                reason="Tiene cuotas mensuales pendientes. Regularice su situación de pagos para acceder a descuentos"
            )
        
        # 3. ❌ VALIDATION: User must have active subscription
        if not user_data.get("subscription_active"):
            return PreFilterResult(
                approved=False,
                rejected=True,
                reason="Su suscripción no está activa. Active su suscripción para solicitar descuentos"
            )
        
        # 4. ❌ VALIDATION: Check for duplicate requests by email (general check)
        # NOTE: Specific show matching is handled by LLM, not PreFilter
        duplicate_check = self._check_for_duplicate_requests_by_user(user_data["id"])
        if duplicate_check["has_recent_duplicate"]:
            return PreFilterResult(
                approved=False,
                rejected=True,
                reason=f"Ya tiene solicitudes de descuento recientes. Espere la respuesta antes de solicitar nuevamente"
            )
        
        # ✅ ALL VALIDATIONS PASSED - Ready for LLM processing
        return PreFilterResult(
            approved=True,
            rejected=False,
            reason="Todas las validaciones de usuario pasaron - listo para análisis de shows por LLM",
            user_data=user_data,
            candidate_shows=None,  # LLM will find shows, not PreFilter
            original_description=show_description,
            ready_for_llm=True
        )
    
    def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user data by email with all required fields"""
        user = self.db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            return None
        
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "city": user.city,
            "subscription_active": user.subscription_active,
            "monthly_fee_current": user.monthly_fee_current,
            "favorite_music_genre": user.favorite_music_genre,
            "registration_date": user.registration_date.isoformat() if user.registration_date else None
        }
    
    def _find_shows_with_discounts(self, description: str, fuzzy_threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        Find shows that match description AND have available discounts
        Uses basic fuzzy matching (LLM will do sophisticated matching later)
        """
        all_shows = self.db.query(Show).filter(Show.active == True).all()
        candidate_shows = []
        
        description_lower = description.lower().strip()
        
        for show in all_shows:
            # Create searchable text
            searchable_text = f"{show.artist} {show.title} {show.venue}".lower()
            
            # Basic fuzzy matching (lower threshold than LLM)
            similarity = fuzz.partial_ratio(description_lower, searchable_text) / 100.0
            
            if similarity >= fuzzy_threshold:
                remaining_discounts = show.get_remaining_discounts(self.db)
                logger.warning(f"🔍 FUZZY MATCH: '{show.title}' similarity={similarity:.2f}, remaining={remaining_discounts}, max={show.max_discounts}")
                
                # ❌ CRITICAL: Only include shows with available discounts
                if remaining_discounts > 0:
                    candidate_shows.append({
                        "id": show.id,
                        "code": show.code,
                        "title": show.title,
                        "artist": show.artist,
                        "venue": show.venue,
                        "show_date": show.show_date.isoformat(),
                        "city": show.other_data.get("city", ""),
                        "max_discounts": show.max_discounts,
                        "remaining_discounts": remaining_discounts,
                        "similarity_score": similarity,
                        "discount_instructions": show.other_data.get("discount_instructions", ""),
                        "price": show.other_data.get("price", 0),
                        "genre": show.other_data.get("genre", "")
                    })
        
        # Sort by similarity score (highest first)
        candidate_shows.sort(key=lambda x: x["similarity_score"], reverse=True)
        return candidate_shows
    
    def _check_for_duplicate_requests_by_user(self, user_id: int) -> Dict[str, Any]:
        """Check if user has recent duplicate requests (any show)"""
        from datetime import datetime, timedelta
        
        # Check for any approved requests in the last 24 hours
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_request = self.db.query(DiscountRequest).filter(
            DiscountRequest.user_id == user_id,
            DiscountRequest.request_date >= recent_cutoff,
            DiscountRequest.human_approved == True  # Only check sent/approved requests
        ).first()
        
        if recent_request:
            return {
                "has_recent_duplicate": True,
                "previous_request_date": recent_request.request_date.isoformat()
            }
        
        return {"has_recent_duplicate": False}
    
    def get_validation_summary(self, result: PreFilterResult) -> Dict[str, Any]:
        """Get detailed summary of validation result for logging/debugging"""
        return {
            "approved": result.approved,
            "rejected": result.rejected,
            "reason": result.reason,
            "user_found": result.user_data is not None,
            "candidate_shows_count": len(result.candidate_shows) if result.candidate_shows else 0,
            "ready_for_llm": result.ready_for_llm,
            "validation_type": "deterministic_prefilter"
        } 