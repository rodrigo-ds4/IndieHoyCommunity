"""
Validation Service
Business rule validations for discount requests
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.database import User, Show, DiscountRequest


class ValidationService:
    """
    Service for validating discount request eligibility
    Checks user status, subscription, limits, show availability
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def validate_discount_request(
        self,
        user_email: str,
        show_id: str,
        request_id: int
    ) -> Dict[str, Any]:
        """
        Main validation method - checks all business rules
        
        Returns:
        {
            "user_valid": bool,
            "subscription_current": bool,
            "within_limits": bool,
            "show_available": bool,
            "discount_applicable": bool,
            "details": {...}
        }
        """
        
        results = {}
        
        # 1. Validate user exists and is active
        user_validation = await self._validate_user(user_email)
        results.update(user_validation)
        
        # 2. Check subscription status
        if results["user_valid"]:
            subscription_validation = await self._validate_subscription(user_email)
            results.update(subscription_validation)
        else:
            results["subscription_current"] = False
        
        # 3. Check discount limits
        if results.get("subscription_current", False):
            limits_validation = await self._validate_discount_limits(user_email)
            results.update(limits_validation)
        else:
            results["within_limits"] = False
        
        # 4. Validate show availability
        show_validation = await self._validate_show(show_id)
        results.update(show_validation)
        
        # 5. Check if discount is applicable for this show
        if results.get("show_available", False):
            discount_validation = await self._validate_discount_applicable(show_id)
            results.update(discount_validation)
        else:
            results["discount_applicable"] = False
        
        return results
    
    async def _validate_user(self, email: str) -> Dict[str, Any]:
        """Check if user exists and is in good standing"""
        
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user:
            return {
                "user_valid": False,
                "user_details": {"error": "User not found", "email": email}
            }
        
        if user.status != "active":
            return {
                "user_valid": False,
                "user_details": {
                    "error": f"User status: {user.status}",
                    "user_id": user.id,
                    "status": user.status
                }
            }
        
        return {
            "user_valid": True,
            "user_details": {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "status": user.status,
                "total_discounts_used": user.total_discounts_used
            }
        }
    
    async def _validate_subscription(self, email: str) -> Dict[str, Any]:
        """Check if user subscription is current and fee is paid"""
        
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return {"subscription_current": False, "subscription_details": {"error": "User not found"}}
        
        # Check if subscription is active
        if not user.subscription_active:
            return {
                "subscription_current": False,
                "subscription_details": {
                    "error": "Subscription inactive",
                    "subscription_active": user.subscription_active
                }
            }
        
        # Check if subscription has expired
        if user.subscription_expiry and user.subscription_expiry < datetime.now():
            return {
                "subscription_current": False,
                "subscription_details": {
                    "error": "Subscription expired",
                    "expiry_date": user.subscription_expiry
                }
            }
        
        # Check if monthly fee is current
        if not user.monthly_fee_current:
            return {
                "subscription_current": False,
                "subscription_details": {
                    "error": "Monthly fee outstanding",
                    "monthly_fee_current": user.monthly_fee_current
                }
            }
        
        return {
            "subscription_current": True,
            "subscription_details": {
                "subscription_active": user.subscription_active,
                "expiry_date": user.subscription_expiry,
                "monthly_fee_current": user.monthly_fee_current
            }
        }
    
    async def _validate_discount_limits(self, email: str) -> Dict[str, Any]:
        """Check if user is within discount limits"""
        
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return {"within_limits": False, "limits_details": {"error": "User not found"}}
        
        # Check monthly limit
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_requests = self.db.query(DiscountRequest).join(User).filter(
            User.email == email,
            DiscountRequest.created_at >= current_month_start,
            DiscountRequest.approved == True
        ).count()
        
        if monthly_requests >= user.max_monthly_discounts:
            return {
                "within_limits": False,
                "limits_details": {
                    "error": "Monthly limit exceeded",
                    "monthly_used": monthly_requests,
                    "monthly_limit": user.max_monthly_discounts
                }
            }
        
        # Additional business rules can be added here
        # e.g., max discount per show, cooldown periods, etc.
        
        return {
            "within_limits": True,
            "limits_details": {
                "monthly_used": monthly_requests,
                "monthly_limit": user.max_monthly_discounts,
                "total_used": user.total_discounts_used
            }
        }
    
    async def _validate_show(self, show_id: str) -> Dict[str, Any]:
        """Check if show exists and is available"""
        
        try:
            show_id_int = int(show_id)
        except ValueError:
            return {
                "show_available": False,
                "show_details": {"error": "Invalid show ID format"}
            }
        
        show = self.db.query(Show).filter(Show.id == show_id_int).first()
        
        if not show:
            return {
                "show_available": False,
                "show_details": {"error": "Show not found", "show_id": show_id}
            }
        
        # Check if show is active
        if not show.active:
            return {
                "show_available": False,
                "show_details": {
                    "error": "Show inactive",
                    "show_id": show.id,
                    "title": show.title
                }
            }
        
        # Check if show date has passed
        if show.date < datetime.now():
            return {
                "show_available": False,
                "show_details": {
                    "error": "Show date has passed",
                    "show_id": show.id,
                    "title": show.title,
                    "date": show.date
                }
            }
        
        # Check if tickets are available
        if show.available_tickets <= 0:
            return {
                "show_available": False,
                "show_details": {
                    "error": "No tickets available",
                    "show_id": show.id,
                    "title": show.title,
                    "available_tickets": show.available_tickets
                }
            }
        
        return {
            "show_available": True,
            "show_details": {
                "show_id": show.id,
                "title": show.title,
                "artist": show.artist,
                "date": show.date,
                "venue": show.venue,
                "base_price": show.base_price,
                "available_tickets": show.available_tickets
            }
        }
    
    async def _validate_discount_applicable(self, show_id: str) -> Dict[str, Any]:
        """Check if discounts are applicable for this show"""
        
        try:
            show_id_int = int(show_id)
        except ValueError:
            return {"discount_applicable": False, "discount_details": {"error": "Invalid show ID"}}
        
        show = self.db.query(Show).filter(Show.id == show_id_int).first()
        
        if not show:
            return {"discount_applicable": False, "discount_details": {"error": "Show not found"}}
        
        # Check if discounts are enabled for this show
        if not show.discount_available:
            return {
                "discount_applicable": False,
                "discount_details": {
                    "error": "Discounts not available for this show",
                    "show_id": show.id,
                    "title": show.title
                }
            }
        
        # Check if show is too close (e.g., no discounts within 24 hours)
        hours_until_show = (show.date - datetime.now()).total_seconds() / 3600
        if hours_until_show < 24:
            return {
                "discount_applicable": False,
                "discount_details": {
                    "error": "Too close to show date for discounts",
                    "hours_until_show": hours_until_show
                }
            }
        
        return {
            "discount_applicable": True,
            "discount_details": {
                "max_discount_percentage": show.max_discount_percentage,
                "hours_until_show": hours_until_show
            }
        }
    
    async def validate_user_quick(self, email: str) -> bool:
        """Quick user validation for simple checks"""
        user = self.db.query(User).filter(User.email == email).first()
        return user is not None and user.status == "active" 