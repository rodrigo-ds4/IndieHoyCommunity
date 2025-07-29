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
        """Mark a reviewed item as sent"""
        try:
            item = self.db.query(SupervisionQueue).filter(SupervisionQueue.id == item_id).first()
            if not item or item.status != "pending" or item.reviewed_at is None:
                logger.error(f"❌ Item {item_id} not found or not ready to send (must be pending and reviewed)")
                return False
            
            item.status = "sent"
            item.email_delivery_status = "sent"  # Nuevo campo
            self.db.commit()
            logger.info(f"📧 Marked item {item_id} as sent with delivery status")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error marking item {item_id} as sent: {str(e)}")
            self.db.rollback()
            return False

    def get_queue_stats(self) -> Dict[str, int]:
        """Get supervision queue statistics"""
        try:
            from sqlalchemy import and_
            
            stats = {
                "approved_pending": self.db.query(SupervisionQueue).filter(
                    and_(
                        SupervisionQueue.decision_type == "approved",
                        SupervisionQueue.status == "pending"
                    )
                ).count(),
                "rejected_pending": self.db.query(SupervisionQueue).filter(
                    and_(
                        SupervisionQueue.decision_type == "rejected", 
                        SupervisionQueue.status == "pending"
                    )
                ).count(),
                "sent": self.db.query(SupervisionQueue).filter(SupervisionQueue.status == "sent").count()
            }
            stats["total"] = sum(stats.values())
            return stats
        except Exception as e:
            logger.error(f"❌ Error getting queue stats: {str(e)}")
            return {"approved_pending": 0, "rejected_pending": 0, "sent": 0, "total": 0}

    def get_filtered_items(self, filters: dict, page: int = 1, page_size: int = 20) -> dict:
        """
        🔍 Obtener items con filtros y paginación avanzada
        
        Args:
            filters: Diccionario con filtros (status, user_email, venue, etc.)
            page: Número de página (1-based)
            page_size: Items por página
            
        Returns:
            dict: Respuesta paginada con items y metadata
        """
        try:
            from sqlalchemy import and_, or_, func
            from app.models.database import Show
            from datetime import datetime
            
            # Base query con JOIN para obtener datos del show
            query = self.db.query(SupervisionQueue)\
                          .outerjoin(Show, SupervisionQueue.show_id == Show.id)
            
            # 🔍 Aplicar filtros
            conditions = []
            
            # Filtro por status
            if filters.get('status'):
                conditions.append(SupervisionQueue.status == filters['status'])
            
            # Filtro por decision_type
            if filters.get('decision_type'):
                conditions.append(SupervisionQueue.decision_type == filters['decision_type'])
            
            # Filtro por email del usuario
            if filters.get('user_email'):
                email_filter = f"%{filters['user_email']}%"
                conditions.append(SupervisionQueue.user_email.ilike(email_filter))
            
            # Filtro por venue (desde show)
            if filters.get('venue'):
                venue_filter = f"%{filters['venue']}%"
                conditions.append(Show.venue.ilike(venue_filter))
            
            # Filtro por título del show
            if filters.get('show_title'):
                title_filter = f"%{filters['show_title']}%"
                conditions.append(
                    or_(
                        Show.title.ilike(title_filter),
                        SupervisionQueue.show_description.ilike(title_filter)
                    )
                )
            
            # Filtro por rango de fechas
            if filters.get('date_from'):
                try:
                    date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d')
                    conditions.append(SupervisionQueue.created_at >= date_from)
                except ValueError:
                    logger.warning(f"Invalid date_from format: {filters['date_from']}")
            
            if filters.get('date_to'):
                try:
                    date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d')
                    # Incluir todo el día
                    date_to = date_to.replace(hour=23, minute=59, second=59)
                    conditions.append(SupervisionQueue.created_at <= date_to)
                except ValueError:
                    logger.warning(f"Invalid date_to format: {filters['date_to']}")
            
            # Aplicar todas las condiciones
            if conditions:
                query = query.filter(and_(*conditions))
            
            # 📊 Contar total de items (antes de paginación)
            total_count = query.count()
            
            # 📄 Aplicar paginación
            offset = (page - 1) * page_size
            items = query.order_by(SupervisionQueue.created_at.desc())\
                        .offset(offset)\
                        .limit(page_size)\
                        .all()
            
            # 🔄 Convertir a diccionarios con datos enriquecidos
            items_data = []
            for item in items:
                # Obtener datos del show si existe
                show_data = None
                if item.show_id:
                    show = self.db.query(Show).filter(Show.id == item.show_id).first()
                    if show:
                        show_data = {
                            "title": show.title,
                            "venue": show.venue,
                            "show_date": show.show_date.isoformat() if show.show_date else None,
                            "artist": show.artist,
                            "max_discounts": show.max_discounts,
                            "remaining_discounts": show.get_remaining_discounts(self.db)
                        }
                
                # Usar el método to_dict() del modelo y agregar datos del show
                item_dict = item.to_dict()
                item_dict["show"] = show_data
                items_data.append(item_dict)
            
            # 📈 Calcular metadata de paginación
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                "items": items_data,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "filters_applied": filters
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting filtered items: {str(e)}")
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
                "error": str(e)
            }

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