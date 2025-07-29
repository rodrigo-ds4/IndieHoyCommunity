"""
Supervision Queue Endpoints
FastAPI endpoints for human supervision of discount decisions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.supervision_queue_service import SupervisionQueueService

router = APIRouter()

class SupervisionAction(BaseModel):
    action: str  # "approve" or "reject"
    reviewer: str
    notes: Optional[str] = None

class EmailEdit(BaseModel):
    email_subject: str
    email_content: str
    decision_type: Optional[str] = None  # "approved" or "rejected"
    reviewer: str
    notes: Optional[str] = None

@router.get("/queue")
async def get_supervision_queue(
    # Filtros
    status: Optional[str] = Query(None, regex="^(pending|approved|rejected|sent)$"),
    decision_type: Optional[str] = Query(None, regex="^(approved|rejected)$"),
    user_email: Optional[str] = Query(None),
    venue: Optional[str] = Query(None),
    show_title: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, regex="^\d{4}-\d{2}-\d{2}$"),
    date_to: Optional[str] = Query(None, regex="^\d{4}-\d{2}-\d{2}$"),
    # Paginación
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    📋 Get items from supervision queue with advanced filtering and pagination
    
    **Filtros disponibles:**
    - **status**: Filter by status (pending, approved, rejected, sent)
    - **user_email**: Filter by user email (partial match)
    - **venue**: Filter by show venue (partial match)
    - **show_title**: Filter by show title (partial match)
    - **date_from**: Filter from date (YYYY-MM-DD)
    - **date_to**: Filter to date (YYYY-MM-DD)
    
    **Paginación:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (1-100, default: 20)
    """
    try:
        supervision_service = SupervisionQueueService(db)
        
        # Construir filtros
        filters = {}
        if status:
            filters['status'] = status
        if decision_type:
            filters['decision_type'] = decision_type
        if user_email:
            filters['user_email'] = user_email
        if venue:
            filters['venue'] = venue
        if show_title:
            filters['show_title'] = show_title
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        # Obtener items filtrados y paginados
        result = supervision_service.get_filtered_items(filters, page, page_size)
        
        return {
            "success": True,
            **result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching queue: {str(e)}")

@router.post("/queue/{item_id}/action")
async def handle_supervision_action(
    item_id: int,
    action: SupervisionAction,
    db: Session = Depends(get_db)
):
    """
    ✅❌ Handle supervision action (approve/reject)
    
    - **item_id**: ID of the queue item
    - **action**: "approve" or "reject"
    - **reviewer**: Name of the reviewer
    - **notes**: Optional notes from reviewer
    """
    try:
        supervision_service = SupervisionQueueService(db)
        
        if action.action == "approve":
            success = supervision_service.approve_item(item_id, action.reviewer, action.notes)
            if success:
                return {
                    "success": True,
                    "message": f"Item {item_id} approved by {action.reviewer}",
                    "action": "approved"
                }
        elif action.action == "reject":
            if not action.notes:
                raise HTTPException(status_code=400, detail="Notes are required for rejection")
            success = supervision_service.reject_item(item_id, action.reviewer, action.notes)
            if success:
                return {
                    "success": True,
                    "message": f"Item {item_id} rejected by {action.reviewer}",
                    "action": "rejected"
                }
        else:
            raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
        
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found or could not be processed")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing action: {str(e)}")

@router.post("/queue/{item_id}/send")
async def mark_as_sent(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    📧 Mark approved or rejected item as sent
    
    - **item_id**: ID of the queue item (approved or rejected)
    """
    try:
        supervision_service = SupervisionQueueService(db)
        success = supervision_service.mark_as_sent(item_id)
        
        if success:
            return {
                "success": True,
                "message": f"Item {item_id} marked as sent",
                "status": "sent"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found or not ready to send")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking as sent: {str(e)}")

@router.get("/stats")
async def get_supervision_stats(db: Session = Depends(get_db)):
    """
    📊 Get supervision queue statistics
    """
    try:
        supervision_service = SupervisionQueueService(db)
        stats = supervision_service.get_queue_stats()
        
        return {
            "success": True,
            "stats": stats,
            "queue_health": {
                "pending_items": stats["approved_pending"] + stats["rejected_pending"],
                "approval_rate": round((stats["approved_pending"] / max(stats["approved_pending"] + stats["rejected_pending"], 1)) * 100, 1),
                "total_processed": stats["sent"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@router.get("/queue/{item_id}")
async def get_queue_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    🔍 Get specific queue item details
    
    - **item_id**: ID of the queue item
    """
    try:
        from app.models.database import SupervisionQueue
        item = db.query(SupervisionQueue).filter(SupervisionQueue.id == item_id).first()
        
        if not item:
            raise HTTPException(status_code=404, detail=f"Queue item {item_id} not found")
        
        return {
            "success": True,
            "item": item.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching item: {str(e)}")

@router.put("/queue/{item_id}/edit")
async def edit_email_content(
    item_id: int,
    edit_data: EmailEdit,
    db: Session = Depends(get_db)
):
    """
    ✏️ Edit email content for a supervision queue item
    
    Allows supervisors to edit the email subject and content before approval.
    """
    try:
        from app.models.database import SupervisionQueue
        from datetime import datetime
        
        # Get the item
        item = db.query(SupervisionQueue).filter(SupervisionQueue.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Allow editing of pending, approved, and rejected items (not sent)
        if item.status == "sent":
            raise HTTPException(status_code=400, detail="Cannot edit items that have already been sent")
        
        # Update the email content
        item.email_subject = edit_data.email_subject
        item.email_content = edit_data.email_content
        if edit_data.decision_type:
            item.decision_type = edit_data.decision_type
        item.supervisor_notes = edit_data.notes
        item.reviewed_by = edit_data.reviewer
        item.reviewed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Email content updated by {edit_data.reviewer}",
            "item": item.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating email: {str(e)}") 