import uuid
from uuid import UUID
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.domain import Notification, QueueToken, Appointment, Branch, Service, Counter, User
from app.services.broadcaster import broadcaster

def create_user_notification(
    db: Session,
    user_id: UUID,
    n_type: str,
    title: str,
    message: str,
    appointment_id: Optional[UUID] = None
) -> Notification:
    """
    Creates and persists a user notification with duplicate spam protection (within 60 seconds).
    Broadcasts real-time alert via live broadcaster.
    """
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(seconds=60)

    # Prevent duplicate spam notifications
    if appointment_id:
        dup_query = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.appointment_id == appointment_id,
            Notification.type == n_type,
            Notification.title == title
        )
        if n_type != "APPOINTMENT_REMINDER":
            dup_query = dup_query.filter(Notification.created_at >= recent_cutoff)
        existing = dup_query.first()
        if existing:
            return existing

    notification = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        appointment_id=appointment_id,
        type=n_type,
        title=title,
        message=message,
        is_read=False,
        sent_at=now,
        created_at=now
    )
    db.add(notification)
    db.flush()

    # Real-time event payload broadcast
    payload = {
        "event": "NOTIFICATION",
        "data": {
            "id": str(notification.id),
            "user_id": str(user_id),
            "appointment_id": str(appointment_id) if appointment_id else None,
            "type": n_type,
            "title": title,
            "message": message,
            "is_read": False,
            "created_at": now.isoformat()
        }
    }
    broadcaster.broadcast_sync_user(str(user_id), payload)
    return notification


def notify_appointment_booked(
    db: Session,
    appt: Appointment,
    service: Optional[Service] = None,
    branch: Optional[Branch] = None
):
    if not appt or not appt.user_id:
        return
    svc_name = service.name if service else "Service"
    branch_name = f"{branch.address}, {branch.city}" if branch else "Branch"
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="APPOINTMENT_BOOKED",
        title=f"Appointment Confirmed: {svc_name}",
        message=f"Your appointment for {svc_name} at {branch_name} on {appt.appointment_date} at {appt.appointment_time} is confirmed.",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "APPOINTMENT_UPDATED",
        "action": "booked",
        "appointment_id": str(appt.id),
        "status": appt.status
    })


def notify_appointment_cancelled(
    db: Session,
    appt: Appointment,
    token: Optional[QueueToken] = None
):
    if not appt or not appt.user_id:
        return
    tok_text = f" (Token {token.token_number})" if token and token.token_number else ""
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="APPOINTMENT_CANCELLED",
        title="Appointment Cancelled",
        message=f"Your appointment on {appt.appointment_date} at {appt.appointment_time}{tok_text} has been cancelled.",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "cancelled",
        "status": "CANCELLED",
        "appointment_id": str(appt.id),
        "token_id": str(token.id) if token else None
    })


def notify_token_generated(
    db: Session,
    token: QueueToken,
    appt: Appointment,
    service: Optional[Service] = None,
    branch: Optional[Branch] = None
):
    if not appt or not appt.user_id:
        return
    svc_name = service.name if service else "Service"
    branch_name = branch.address if branch else "Branch"
    pos = token.queue_position or 1
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="TOKEN_CREATED",
        title=f"Token {token.token_number} Issued",
        message=f"Your queue token {token.token_number} has been created for {svc_name} at {branch_name}. Position #{pos} in line.",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "token_created",
        "status": token.status,
        "token_id": str(token.id),
        "token_number": token.token_number,
        "appointment_id": str(appt.id),
        "queue_position": token.queue_position,
        "estimated_waiting_time": token.estimated_waiting_time
    })


def notify_token_called(
    db: Session,
    token: QueueToken,
    appt: Appointment,
    counter_name: str,
    counter_number: int
):
    if not appt or not appt.user_id:
        return
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="CALLED",
        title=f"🔔 NOW CALLING: Token {token.token_number}",
        message=f"It is your turn! Please proceed immediately to Counter #{counter_number} ({counter_name}).",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "called",
        "status": "CALLED",
        "token_id": str(token.id),
        "token_number": token.token_number,
        "appointment_id": str(appt.id),
        "counter_name": counter_name,
        "counter_number": counter_number
    })


def notify_approaching_turn(
    db: Session,
    token: QueueToken,
    appt: Appointment,
    people_ahead: int
):
    if not appt or not appt.user_id:
        return
    pos = people_ahead + 1
    unit_str = "person" if people_ahead == 1 else "people"
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="TURN_ALERT",
        title=f"⚠️ Approaching Turn: Token {token.token_number}",
        message=f"You are #{pos} in queue ({people_ahead} {unit_str} ahead). Please prepare to approach your service desk.",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "turn_alert",
        "status": token.status,
        "token_id": str(token.id),
        "token_number": token.token_number,
        "appointment_id": str(appt.id),
        "people_ahead": people_ahead,
        "queue_position": pos
    })


def notify_service_started(
    db: Session,
    token: QueueToken,
    appt: Appointment,
    counter_name: Optional[str] = "Service Desk"
):
    if not appt or not appt.user_id:
        return
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="SERVING",
        title=f"Service Started: {token.token_number}",
        message=f"Your consultation has started at {counter_name}.",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "started",
        "status": "SERVING",
        "token_id": str(token.id),
        "token_number": token.token_number,
        "appointment_id": str(appt.id),
        "counter_name": counter_name
    })


def notify_service_completed(
    db: Session,
    token: QueueToken,
    appt: Appointment
):
    if not appt or not appt.user_id:
        return
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="COMPLETED",
        title=f"Service Completed: {token.token_number}",
        message=f"Your service session has ended. Thank you for using QueueLess AI!",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "completed",
        "status": "COMPLETED",
        "token_id": str(token.id),
        "token_number": token.token_number,
        "appointment_id": str(appt.id)
    })
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "APPOINTMENT_UPDATED",
        "action": "completed",
        "status": "COMPLETED",
        "id": str(appt.id),
        "appointment_id": str(appt.id),
        "token_id": str(token.id),
        "token_number": token.token_number
    })


def notify_token_skipped(
    db: Session,
    token: QueueToken,
    appt: Appointment
):
    if not appt or not appt.user_id:
        return
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="SKIPPED",
        title=f"Token {token.token_number} Skipped",
        message=f"Your token was skipped because you were not present when called. Please speak with staff to be recalled.",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "skipped",
        "status": "SKIPPED",
        "token_id": str(token.id),
        "token_number": token.token_number,
        "appointment_id": str(appt.id)
    })


def notify_token_no_show(
    db: Session,
    token: QueueToken,
    appt: Appointment
):
    if not appt or not appt.user_id:
        return
    create_user_notification(
        db=db,
        user_id=appt.user_id,
        n_type="NO_SHOW",
        title=f"Token {token.token_number} Marked No-Show",
        message=f"Your appointment was marked as No-Show. Please book a new slot if needed.",
        appointment_id=appt.id
    )
    broadcaster.broadcast_sync_user(str(appt.user_id), {
        "event": "QUEUE_UPDATED",
        "action": "no_show",
        "status": "NO_SHOW",
        "token_id": str(token.id),
        "token_number": token.token_number,
        "appointment_id": str(appt.id)
    })


def dispatch_approaching_queue_alerts(
    db: Session,
    branch_id: UUID,
    target_date: date
):
    """
    Scans the next 2 WAITING tokens in line for this branch today,
    and dispatches proactive approaching turn alerts to keep customers prepared.
    """
    next_waiting = (
        db.query(QueueToken)
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(
            Appointment.branch_id == branch_id,
            Appointment.appointment_date == target_date,
            QueueToken.status == 'WAITING'
        )
        .order_by(
            Appointment.appointment_time.asc(),
            QueueToken.created_at.asc(),
            QueueToken.id.asc()
        )
        .limit(2)
        .all()
    )

    for idx, tok in enumerate(next_waiting):
        if tok.appointment:
            # idx=0 means next (0 ahead), idx=1 means 1 ahead
            notify_approaching_turn(db, tok, tok.appointment, people_ahead=idx)
