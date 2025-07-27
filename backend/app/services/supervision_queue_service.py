"""
Supervision Queue Service
Manages the human supervision queue for discount responses
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import SupervisionQueue, Show, User

logger = logging.getLogger(__name__)

class SupervisionQueueService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def add_to_queue(self, decision_data: Dict[str, Any]) -> SupervisionQueue:
        """Add a discount decision to the supervision queue"""
        try:
            # Extract email subject based on decision type
            email_subject = self._generate_email_subject(decision_data)
            
            # Create queue item
            queue_item = SupervisionQueue(
                request_id=decision_data.get("request_id", f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                user_email=decision_data.get("user_email"),
                user_name=decision_data.get("user_name", "Usuario"),
                show_description=decision_data.get("show_description"),
                decision_type=decision_data.get("decision_type"),
                decision_source=decision_data.get("decision_source", "llm_generated"),
                show_id=decision_data.get("show_id"),
                email_subject=email_subject,
                email_content=decision_data.get("email_content"),
                confidence_score=decision_data.get("confidence"),
                reasoning=decision_data.get("reasoning"),
                processing_time=decision_data.get("processing_time", 0),
                status="pending"
            )
            
            self.db.add(queue_item)
            self.db.commit()
            self.db.refresh(queue_item)
            
            logger.info(f"✅ Added to supervision queue: {queue_item.request_id} - {decision_data.get('decision')}")
            return queue_item
            
        except Exception as e:
            logger.error(f"❌ Error adding to supervision queue: {str(e)}")
            self.db.rollback()
            raise

    def get_pending_items(self, limit: int = 50) -> List[SupervisionQueue]:
        """Get pending items from supervision queue"""
        try:
            items = self.db.query(SupervisionQueue)\
                          .filter(SupervisionQueue.status == "pending")\
                          .order_by(SupervisionQueue.created_at.desc())\
                          .limit(limit)\
                          .all()
            return items
        except Exception as e:
            logger.error(f"❌ Error fetching pending items: {str(e)}")
            return []

    def approve_item(self, item_id: int, reviewer: str, notes: str = None) -> bool:
        """Approve an item and mark it for sending"""
        try:
            item = self.db.query(SupervisionQueue).filter(SupervisionQueue.id == item_id).first()
            if not item:
                logger.error(f"❌ Item {item_id} not found")
                return False
            
            item.status = "approved"
            item.reviewed_at = datetime.utcnow()
            item.reviewed_by = reviewer
            item.supervisor_notes = notes
            
            self.db.commit()
            logger.info(f"✅ Approved item {item_id} by {reviewer}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error approving item {item_id}: {str(e)}")
            self.db.rollback()
            return False

    def reject_item(self, item_id: int, reviewer: str, notes: str) -> bool:
        """Reject an item"""
        try:
            item = self.db.query(SupervisionQueue).filter(SupervisionQueue.id == item_id).first()
            if not item:
                logger.error(f"❌ Item {item_id} not found")
                return False
            
            item.status = "rejected"
            item.reviewed_at = datetime.utcnow()
            item.reviewed_by = reviewer
            item.supervisor_notes = notes
            
            self.db.commit()
            logger.info(f"❌ Rejected item {item_id} by {reviewer}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error rejecting item {item_id}: {str(e)}")
            self.db.rollback()
            return False

    def mark_as_sent(self, item_id: int) -> bool:
        """Mark an approved item as sent"""
        try:
            item = self.db.query(SupervisionQueue).filter(SupervisionQueue.id == item_id).first()
            if not item or item.status != "approved":
                logger.error(f"❌ Item {item_id} not found or not approved")
                return False
            
            item.status = "sent"
            self.db.commit()
            logger.info(f"📧 Marked item {item_id} as sent")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error marking item {item_id} as sent: {str(e)}")
            self.db.rollback()
            return False

    def get_queue_stats(self) -> Dict[str, int]:
        """Get supervision queue statistics"""
        try:
            stats = {
                "pending": self.db.query(SupervisionQueue).filter(SupervisionQueue.status == "pending").count(),
                "approved": self.db.query(SupervisionQueue).filter(SupervisionQueue.status == "approved").count(),
                "rejected": self.db.query(SupervisionQueue).filter(SupervisionQueue.status == "rejected").count(),
                "sent": self.db.query(SupervisionQueue).filter(SupervisionQueue.status == "sent").count()
            }
            stats["total"] = sum(stats.values())
            return stats
        except Exception as e:
            logger.error(f"❌ Error getting queue stats: {str(e)}")
            return {"pending": 0, "approved": 0, "rejected": 0, "sent": 0, "total": 0}

    def _generate_email_subject(self, decision_data: Dict[str, Any]) -> str:
        """Generate email subject based on decision type"""
        decision_type = decision_data.get("decision_type", "unknown")
        show_description = decision_data.get("show_description", "Show")
        
        subjects = {
            "approved": f"✅ Descuento aprobado - {show_description}",
            "rejected": f"❌ Solicitud de descuento - {show_description}",
            "needs_clarification": f"🤔 Necesitamos más información - {show_description}"
        }
        
        return subjects.get(decision_type, f"📧 Respuesta a solicitud - {show_description}") 