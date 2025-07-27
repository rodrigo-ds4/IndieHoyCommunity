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

@router.get("/queue")
async def get_supervision_queue(
    limit: int = Query(50, ge=1, le=100),
    status: str = Query("pending", regex="^(pending|approved|rejected|sent)$"),
    db: Session = Depends(get_db)
):
    """
    📋 Get items from supervision queue
    
    - **limit**: Maximum number of items to return (1-100)
    - **status**: Filter by status (pending, approved, rejected, sent)
    """
    try:
        supervision_service = SupervisionQueueService(db)
        
        if status == "pending":
            items = supervision_service.get_pending_items(limit)
        else:
            # Get items by specific status
            from app.models.database import SupervisionQueue
            items = db.query(SupervisionQueue)\
                     .filter(SupervisionQueue.status == status)\
                     .order_by(SupervisionQueue.created_at.desc())\
                     .limit(limit)\
                     .all()
        
        return {
            "success": True,
            "items": [item.to_dict() for item in items],
            "count": len(items),
            "status_filter": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supervision queue: {str(e)}")

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
    📧 Mark approved item as sent
    
    - **item_id**: ID of the approved queue item
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
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found or not approved")
            
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
                "pending_items": stats["pending"],
                "approval_rate": round((stats["approved"] / max(stats["total"], 1)) * 100, 1),
                "total_processed": stats["approved"] + stats["rejected"]
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