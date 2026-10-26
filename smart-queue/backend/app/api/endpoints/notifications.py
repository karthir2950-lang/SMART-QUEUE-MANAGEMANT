from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.domain import User, Notification
from app.schemas.notification import NotificationResponse, NotificationListResponse

router = APIRouter()

@router.get("", response_model=NotificationListResponse)
def get_user_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    if unread_only:
        query = query.filter(Notification.is_read == False)

    total_count = query.count()
    items = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

    return NotificationListResponse(
        notifications=items,
        total_count=total_count,
        unread_count=unread_count
    )

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(notif.user_id) != str(current_user.id) and current_user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Unauthorized access to notification")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read", "updated_count": updated}

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(notif.user_id) != str(current_user.id) and current_user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Unauthorized access to notification")

    db.delete(notif)
    db.commit()
    return {"message": "Notification deleted successfully"}
