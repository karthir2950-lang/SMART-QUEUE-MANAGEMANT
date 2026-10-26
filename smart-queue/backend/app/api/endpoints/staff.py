from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from typing import List, Optional
from datetime import date, datetime, timezone
import uuid
from uuid import UUID

from app.db.database import get_db
from app.core.security import require_staff, get_current_user
from app.models.domain import (
    User, Staff, Counter, Branch, Organization, Appointment, QueueToken, QueueEvent
)
from app.schemas.admin import (
    StaffDashboardSummary, AppointmentAdminResponse, TokenAdminResponse
)
from app.schemas.queue import (
    StaffQueueResponse, StaffQueueItem, StaffCounterInfo
)

router = APIRouter()

def get_staff_context(db: Session, user: User) -> Staff:
    """Finds and verifies the staff record and branch authorization for the authenticated user."""
    staff = db.query(Staff).filter(Staff.user_id == user.id, Staff.status == 'ACTIVE').first()
    if not staff:
        # If user is ADMIN accessing staff view for demo/inspection, find the first active branch
        if user.role == 'ADMIN':
            first_branch = db.query(Branch).filter(Branch.status == 'ACTIVE').first()
            if first_branch:
                # Return dummy staff wrapper
                dummy = Staff(
                    id=user.id,
                    user_id=user.id,
                    organization_id=first_branch.organization_id,
                    branch_id=first_branch.id,
                    role="STAFF",
                    status="ACTIVE"
                )
                dummy.branch = first_branch
                dummy.organization = first_branch.organization
                dummy.user = user
                return dummy
        raise HTTPException(
            status_code=403,
            detail="User is not assigned as active staff to any organization or branch"
        )
    return staff


@router.get("/dashboard/summary", response_model=StaffDashboardSummary)
def get_staff_dashboard_summary(
    branch_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)
    if branch_id and branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to other branch")
    branch = db.query(Branch).filter(Branch.id == staff.branch_id).first()
    org = db.query(Organization).filter(Organization.id == staff.organization_id).first()

    today = date.today()

    # Scope all queries strictly to staff's authorized branch
    today_appts = db.query(Appointment).filter(
        Appointment.branch_id == staff.branch_id,
        Appointment.appointment_date == today
    ).count()

    waiting_tokens = db.query(QueueToken).join(Appointment).filter(
        Appointment.branch_id == staff.branch_id,
        Appointment.appointment_date == today,
        QueueToken.status.in_(['WAITING', 'CALLED'])
    ).count()

    completed_today = db.query(Appointment).filter(
        Appointment.branch_id == staff.branch_id,
        Appointment.appointment_date == today,
        Appointment.status == 'COMPLETED'
    ).count()

    # Find any counter in this branch
    counter = db.query(Counter).filter(Counter.branch_id == staff.branch_id).first()
    counter_name = f"Counter #{counter.counter_number} ({counter.name})" if counter else "General Counter"

    return StaffDashboardSummary(
        staff_name=current_user.name,
        staff_email=current_user.email,
        organization_name=org.name if org else "Assigned Organization",
        branch_name=branch.address if branch else "Assigned Branch",
        branch_city=branch.city if branch else "",
        assigned_counter=counter_name,
        today_appointments=today_appts,
        waiting_tokens=waiting_tokens,
        completed_today=completed_today
    )


@router.get("/appointments", response_model=List[AppointmentAdminResponse])
def get_staff_appointments(
    target_date: Optional[date] = None,
    service_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)
    if branch_id and branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to other branch")

    # Strictly enforce branch_id = staff.branch_id
    query = db.query(Appointment).filter(Appointment.branch_id == staff.branch_id)

    if target_date:
        query = query.filter(Appointment.appointment_date == target_date)
    if service_id:
        query = query.filter(Appointment.service_id == service_id)
    if status:
        query = query.filter(Appointment.status == status)

    records = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).offset(skip).limit(limit).all()
    out = []
    for a in records:
        out.append(AppointmentAdminResponse(
            id=a.id,
            user_id=a.user_id,
            user_name=a.user.name if a.user else "User",
            sector_name=a.sector.name if a.sector else "",
            organization_name=a.organization.name if a.organization else "",
            branch_name=f"{a.branch.address}, {a.branch.city}" if a.branch else "",
            service_name=a.service.name if a.service else "",
            appointment_date=a.appointment_date,
            appointment_time=a.appointment_time,
            status=a.status,
            notes=a.notes,
            created_at=a.created_at
        ))
    return out


@router.get("/tokens", response_model=List[TokenAdminResponse])
def get_staff_tokens(
    target_date: Optional[date] = None,
    service_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)
    if branch_id and branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to other branch")

    # Strictly enforce staff's branch_id
    query = db.query(QueueToken).join(Appointment).filter(Appointment.branch_id == staff.branch_id)

    if target_date:
        query = query.filter(Appointment.appointment_date == target_date)
    if service_id:
        query = query.filter(Appointment.service_id == service_id)
    if status:
        query = query.filter(QueueToken.status == status)

    tokens = query.order_by(QueueToken.created_at.desc()).offset(skip).limit(limit).all()
    out = []
    for t in tokens:
        out.append(TokenAdminResponse(
            id=t.id,
            appointment_id=t.appointment_id,
            token_number=t.token_number,
            service_name=t.appointment.service.name if t.appointment and t.appointment.service else "",
            branch_name=f"{t.appointment.branch.address}, {t.appointment.branch.city}" if t.appointment and t.appointment.branch else "",
            appointment_date=t.appointment.appointment_date if t.appointment else None,
            status=t.status,
            queue_position=t.queue_position,
            estimated_waiting_time=t.estimated_waiting_time,
            created_at=t.created_at
        ))
    return out


# =====================================================================
# QUEUE OPERATION ENGINE (STEP 8)
# =====================================================================

def recalculate_branch_queue_positions(db: Session, branch_id: UUID, target_date: date):
    """
    Recalculates deterministic queue positions (1, 2, 3...) for all active WAITING tokens
    in the branch on target date.
    """
    waiting_tokens = (
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
        .all()
    )
    for idx, tok in enumerate(waiting_tokens, start=1):
        tok.queue_position = idx


def format_queue_item(tok: Optional[QueueToken]) -> Optional[StaffQueueItem]:
    if not tok:
        return None
    appt = tok.appointment
    counter = tok.counter
    return StaffQueueItem(
        id=tok.id,
        appointment_id=tok.appointment_id,
        token_number=tok.token_number,
        user_name=appt.user.name if appt and appt.user else "Customer",
        service_name=appt.service.name if appt and appt.service else "Service",
        queue_position=tok.queue_position,
        status=tok.status,
        counter_id=tok.counter_id,
        counter_number=counter.counter_number if counter else None,
        counter_name=counter.name if counter else None,
        called_at=tok.called_at,
        started_at=tok.started_at,
        completed_at=tok.completed_at,
        estimated_waiting_time=tok.estimated_waiting_time,
        appointment_time=appt.appointment_time if appt else None,
        appointment_date=appt.appointment_date if appt else None,
        created_at=tok.created_at
    )


@router.get("/queue", response_model=StaffQueueResponse)
def get_staff_queue(
    counter_id: Optional[UUID] = Query(None),
    branch_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)
    if branch_id and branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to other branch")
    branch = db.query(Branch).filter(Branch.id == staff.branch_id).first()
    org = db.query(Organization).filter(Organization.id == staff.organization_id).first()
    today = date.today()

    counter = None
    if counter_id:
        counter = db.query(Counter).filter(Counter.id == counter_id, Counter.branch_id == staff.branch_id).first()
        if not counter:
            raise HTTPException(status_code=404, detail="Counter not found or not in authorized branch")
    else:
        counter = db.query(Counter).filter(Counter.branch_id == staff.branch_id).order_by(Counter.counter_number.asc()).first()

    current_token = None
    if counter:
        if counter.current_token_id:
            current_token = db.query(QueueToken).filter(
                QueueToken.id == counter.current_token_id,
                QueueToken.status.in_(['CALLED', 'SERVING'])
            ).first()
        if not current_token:
            current_token = (
                db.query(QueueToken)
                .join(Appointment, QueueToken.appointment_id == Appointment.id)
                .filter(
                    QueueToken.counter_id == counter.id,
                    QueueToken.status.in_(['CALLED', 'SERVING']),
                    Appointment.branch_id == staff.branch_id,
                    Appointment.appointment_date == today
                )
                .order_by(QueueToken.called_at.desc(), QueueToken.updated_at.desc())
                .first()
            )

    waiting_tokens = (
        db.query(QueueToken)
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(
            Appointment.branch_id == staff.branch_id,
            Appointment.appointment_date == today,
            QueueToken.status == 'WAITING'
        )
        .order_by(
            Appointment.appointment_time.asc(),
            QueueToken.created_at.asc(),
            QueueToken.id.asc()
        )
        .limit(50)
        .all()
    )

    waiting_count = (
        db.query(QueueToken)
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(
            Appointment.branch_id == staff.branch_id,
            Appointment.appointment_date == today,
            QueueToken.status == 'WAITING'
        )
        .count()
    )

    completed_count = (
        db.query(QueueToken)
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(
            Appointment.branch_id == staff.branch_id,
            Appointment.appointment_date == today,
            QueueToken.status == 'COMPLETED'
        )
        .count()
    )

    serving_count = (
        db.query(QueueToken)
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(
            Appointment.branch_id == staff.branch_id,
            Appointment.appointment_date == today,
            QueueToken.status.in_(['CALLED', 'SERVING'])
        )
        .count()
    )

    counter_info = None
    if counter:
        counter_info = StaffCounterInfo(
            id=counter.id,
            counter_number=counter.counter_number,
            name=counter.name,
            status=counter.status,
            current_token_id=current_token.id if current_token else None
        )

    return StaffQueueResponse(
        organization_name=org.name if org else "",
        branch_name=branch.address if branch else "",
        branch_city=branch.city if branch else "",
        assigned_counter=counter_info,
        current_token=format_queue_item(current_token),
        waiting_tokens=[format_queue_item(t) for t in waiting_tokens],
        waiting_count=waiting_count,
        today_completed_count=completed_count,
        today_serving_count=serving_count
    )


@router.post("/queue/call-next", response_model=StaffQueueItem)
def staff_call_next(
    counter_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)
    today = date.today()

    # 1. Resolve and validate counter with row lock
    if counter_id:
        counter = db.query(Counter).filter(Counter.id == counter_id).with_for_update().first()
        if not counter:
            raise HTTPException(status_code=404, detail="Counter not found")
        if counter.branch_id != staff.branch_id:
            raise HTTPException(status_code=403, detail="Unauthorized counter for this branch")
    else:
        counter = (
            db.query(Counter)
            .filter(Counter.branch_id == staff.branch_id)
            .order_by(Counter.counter_number.asc())
            .with_for_update()
            .first()
        )
        if not counter:
            counter = Counter(
                id=uuid.uuid4(),
                branch_id=staff.branch_id,
                counter_number=1,
                name="Desk #1",
                status="AVAILABLE"
            )
            db.add(counter)
            db.flush()

    if counter.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Assigned counter is currently closed")

    # 2. Prevent counter from serving two tokens simultaneously
    if counter.current_token_id:
        active_tok = db.query(QueueToken).filter(
            QueueToken.id == counter.current_token_id,
            QueueToken.status.in_(['CALLED', 'SERVING'])
        ).first()
        if active_tok:
            raise HTTPException(
                status_code=409,
                detail=f"Counter #{counter.counter_number} is already serving token {active_tok.token_number}. Please complete or skip it before calling next."
            )

    # 3. Deterministically select earliest WAITING token with row locking (skip locked)
    next_token = (
        db.query(QueueToken)
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(
            Appointment.branch_id == staff.branch_id,
            Appointment.appointment_date == today,
            QueueToken.status == 'WAITING'
        )
        .order_by(
            Appointment.appointment_time.asc(),
            QueueToken.created_at.asc(),
            QueueToken.id.asc()
        )
        .with_for_update(skip_locked=True)
        .first()
    )

    if not next_token:
        raise HTTPException(status_code=404, detail="No waiting tokens available.")

    # 4. Atomic Transition: WAITING -> CALLED
    prev_status = next_token.status
    next_token.status = 'CALLED'
    next_token.counter_id = counter.id
    next_token.called_at = datetime.now(timezone.utc)
    next_token.queue_position = None

    if next_token.appointment:
        next_token.appointment.status = 'CALLED'

    counter.current_token_id = next_token.id
    counter.status = 'BUSY'

    # 5. Record QueueEvent
    event = QueueEvent(
        id=uuid.uuid4(),
        token_id=next_token.id,
        event_type='CALLED',
        previous_status=prev_status,
        new_status='CALLED',
        counter_id=counter.id,
        performed_by=current_user.id,
        metadata_={"counter_number": counter.counter_number, "action": "call_next"}
    )
    db.add(event)

    # 6. Recalculate queue positions
    recalculate_branch_queue_positions(db, staff.branch_id, today)

    # 7. Step 9: Real-time Notifications & Branch Broadcast
    try:
        from app.services.notification_service import notify_token_called, dispatch_approaching_queue_alerts
        from app.services.broadcaster import broadcaster
        notify_token_called(db, next_token, next_token.appointment, counter.name, counter.counter_number)
        dispatch_approaching_queue_alerts(db, staff.branch_id, today)
        broadcaster.broadcast_sync_branch(str(staff.branch_id), {
            "event": "QUEUE_UPDATED",
            "action": "call_next",
            "token_id": str(next_token.id),
            "token_number": next_token.token_number,
            "counter_number": counter.counter_number
        })
    except Exception:
        pass

    db.commit()
    db.refresh(next_token)
    return format_queue_item(next_token)


@router.post("/queue/{token_id}/start", response_model=StaffQueueItem)
def staff_start_serving(
    token_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)

    token = db.query(QueueToken).filter(QueueToken.id == token_id).with_for_update().first()
    if not token:
        raise HTTPException(status_code=404, detail="Queue token not found")

    if not token.appointment or token.appointment.branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Token belongs to another branch")

    # Guard transitions
    if token.status == 'WAITING':
        raise HTTPException(status_code=409, detail="Token must be CALLED before starting service.")
    if token.status == 'COMPLETED':
        raise HTTPException(status_code=409, detail="Cannot transition COMPLETED token to SERVING.")
    if token.status == 'SKIPPED':
        raise HTTPException(status_code=409, detail="Cannot transition SKIPPED token directly to SERVING.")
    if token.status == 'NO_SHOW':
        raise HTTPException(status_code=409, detail="Cannot transition NO_SHOW token directly to SERVING.")
    if token.status == 'CANCELLED':
        raise HTTPException(status_code=409, detail="Cannot transition CANCELLED token to SERVING.")
    if token.status != 'CALLED':
        raise HTTPException(status_code=409, detail=f"Invalid transition from {token.status} to SERVING.")

    # Atomic Transition: CALLED -> SERVING
    prev_status = token.status
    token.status = 'SERVING'
    token.started_at = datetime.now(timezone.utc)
    token.queue_position = None

    if token.appointment:
        token.appointment.status = 'SERVING'

    if token.counter_id:
        counter = db.query(Counter).filter(Counter.id == token.counter_id).first()
        if counter:
            counter.current_token_id = token.id
            counter.status = 'BUSY'

    event = QueueEvent(
        id=uuid.uuid4(),
        token_id=token.id,
        event_type='SERVING',
        previous_status=prev_status,
        new_status='SERVING',
        counter_id=token.counter_id,
        performed_by=current_user.id,
        metadata_={"action": "start_serving"}
    )
    db.add(event)

    # Step 9: Notifications & Live Sync
    try:
        from app.services.notification_service import notify_service_started
        from app.services.broadcaster import broadcaster
        c_name = "Service Desk"
        if token.counter_id:
            c_obj = db.query(Counter).filter(Counter.id == token.counter_id).first()
            if c_obj:
                c_name = f"Counter #{c_obj.counter_number} ({c_obj.name})"
        notify_service_started(db, token, token.appointment, c_name)
        broadcaster.broadcast_sync_branch(str(staff.branch_id), {
            "event": "QUEUE_UPDATED",
            "action": "start_serving",
            "token_id": str(token.id),
            "token_number": token.token_number
        })
    except Exception:
        pass

    db.commit()
    db.refresh(token)
    return format_queue_item(token)


@router.post("/queue/{token_id}/complete", response_model=StaffQueueItem)
def staff_complete_serving(
    token_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)

    token = db.query(QueueToken).filter(QueueToken.id == token_id).with_for_update().first()
    if not token:
        raise HTTPException(status_code=404, detail="Queue token not found")

    if not token.appointment or token.appointment.branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Token belongs to another branch")

    # Guard transitions
    if token.status == 'COMPLETED':
        raise HTTPException(status_code=409, detail="Token is already COMPLETED.")
    if token.status == 'WAITING':
        raise HTTPException(status_code=409, detail="Cannot complete a token that is still WAITING.")
    if token.status in ['SKIPPED', 'NO_SHOW', 'CANCELLED']:
        raise HTTPException(status_code=409, detail=f"Cannot complete token in {token.status} status.")
    if token.status not in ['SERVING', 'CALLED']:
        raise HTTPException(status_code=409, detail=f"Invalid transition from {token.status} to COMPLETED.")

    prev_status = token.status
    token.status = 'COMPLETED'
    token.completed_at = datetime.now(timezone.utc)
    token.queue_position = None

    if token.appointment:
        token.appointment.status = 'COMPLETED'

    if token.counter_id:
        counter = db.query(Counter).filter(Counter.id == token.counter_id).first()
        if counter and counter.current_token_id == token.id:
            counter.current_token_id = None
            counter.status = 'AVAILABLE'

    event = QueueEvent(
        id=uuid.uuid4(),
        token_id=token.id,
        event_type='COMPLETED',
        previous_status=prev_status,
        new_status='COMPLETED',
        counter_id=token.counter_id,
        performed_by=current_user.id,
        metadata_={"action": "complete"}
    )
    db.add(event)

    if token.appointment:
        recalculate_branch_queue_positions(db, staff.branch_id, token.appointment.appointment_date)

    # Step 9: Notifications & Live Sync
    try:
        from app.services.notification_service import notify_service_completed, dispatch_approaching_queue_alerts
        from app.services.broadcaster import broadcaster
        notify_service_completed(db, token, token.appointment)
        if token.appointment:
            dispatch_approaching_queue_alerts(db, staff.branch_id, token.appointment.appointment_date)
        broadcaster.broadcast_sync_branch(str(staff.branch_id), {
            "event": "QUEUE_UPDATED",
            "action": "complete",
            "token_id": str(token.id),
            "token_number": token.token_number
        })
    except Exception:
        pass

    db.commit()
    db.refresh(token)
    return format_queue_item(token)


@router.post("/queue/{token_id}/skip", response_model=StaffQueueItem)
def staff_skip_token(
    token_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)

    token = db.query(QueueToken).filter(QueueToken.id == token_id).with_for_update().first()
    if not token:
        raise HTTPException(status_code=404, detail="Queue token not found")

    if not token.appointment or token.appointment.branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Token belongs to another branch")

    # Guard transitions: only WAITING or CALLED can be skipped
    if token.status == 'COMPLETED':
        raise HTTPException(status_code=409, detail="Cannot skip a COMPLETED token.")
    if token.status == 'SERVING':
        raise HTTPException(status_code=409, detail="Cannot skip a token currently in SERVING status. Please complete it.")
    if token.status not in ['WAITING', 'CALLED']:
        raise HTTPException(status_code=409, detail=f"Cannot skip token in {token.status} status.")

    prev_status = token.status
    token.status = 'SKIPPED'
    token.queue_position = None

    if token.appointment:
        token.appointment.status = 'SKIPPED'

    if token.counter_id:
        counter = db.query(Counter).filter(Counter.id == token.counter_id).first()
        if counter and counter.current_token_id == token.id:
            counter.current_token_id = None
            counter.status = 'AVAILABLE'

    event = QueueEvent(
        id=uuid.uuid4(),
        token_id=token.id,
        event_type='SKIPPED',
        previous_status=prev_status,
        new_status='SKIPPED',
        counter_id=token.counter_id,
        performed_by=current_user.id,
        metadata_={"action": "skip"}
    )
    db.add(event)

    if token.appointment:
        recalculate_branch_queue_positions(db, staff.branch_id, token.appointment.appointment_date)

    # Step 9: Notifications & Live Sync
    try:
        from app.services.notification_service import notify_token_skipped, dispatch_approaching_queue_alerts
        from app.services.broadcaster import broadcaster
        notify_token_skipped(db, token, token.appointment)
        if token.appointment:
            dispatch_approaching_queue_alerts(db, staff.branch_id, token.appointment.appointment_date)
        broadcaster.broadcast_sync_branch(str(staff.branch_id), {
            "event": "QUEUE_UPDATED",
            "action": "skip",
            "token_id": str(token.id),
            "token_number": token.token_number
        })
    except Exception:
        pass

    db.commit()
    db.refresh(token)
    return format_queue_item(token)


@router.post("/queue/{token_id}/no-show", response_model=StaffQueueItem)
def staff_mark_no_show(
    token_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    staff = get_staff_context(db, current_user)

    token = db.query(QueueToken).filter(QueueToken.id == token_id).with_for_update().first()
    if not token:
        raise HTTPException(status_code=404, detail="Queue token not found")

    if not token.appointment or token.appointment.branch_id != staff.branch_id:
        raise HTTPException(status_code=403, detail="Token belongs to another branch")

    # Guard transitions: only WAITING or CALLED can be marked NO_SHOW
    if token.status == 'COMPLETED':
        raise HTTPException(status_code=409, detail="Cannot mark a COMPLETED token as NO_SHOW.")
    if token.status == 'SERVING':
        raise HTTPException(status_code=409, detail="Cannot mark a token in SERVING status as NO_SHOW.")
    if token.status not in ['WAITING', 'CALLED']:
        raise HTTPException(status_code=409, detail=f"Cannot mark token in {token.status} status as NO_SHOW.")

    prev_status = token.status
    token.status = 'NO_SHOW'
    token.queue_position = None

    if token.appointment:
        token.appointment.status = 'NO_SHOW'

    if token.counter_id:
        counter = db.query(Counter).filter(Counter.id == token.counter_id).first()
        if counter and counter.current_token_id == token.id:
            counter.current_token_id = None
            counter.status = 'AVAILABLE'

    event = QueueEvent(
        id=uuid.uuid4(),
        token_id=token.id,
        event_type='NO_SHOW',
        previous_status=prev_status,
        new_status='NO_SHOW',
        counter_id=token.counter_id,
        performed_by=current_user.id,
        metadata_={"action": "no_show"}
    )
    db.add(event)

    if token.appointment:
        recalculate_branch_queue_positions(db, staff.branch_id, token.appointment.appointment_date)

    # Step 9: Notifications & Live Sync
    try:
        from app.services.notification_service import notify_token_no_show, dispatch_approaching_queue_alerts
        from app.services.broadcaster import broadcaster
        notify_token_no_show(db, token, token.appointment)
        if token.appointment:
            dispatch_approaching_queue_alerts(db, staff.branch_id, token.appointment.appointment_date)
        broadcaster.broadcast_sync_branch(str(staff.branch_id), {
            "event": "QUEUE_UPDATED",
            "action": "no_show",
            "token_id": str(token.id),
            "token_number": token.token_number
        })
    except Exception:
        pass

    db.commit()
    db.refresh(token)
    return format_queue_item(token)
