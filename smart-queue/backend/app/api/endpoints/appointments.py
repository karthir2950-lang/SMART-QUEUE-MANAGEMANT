from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, cast, Date, text
from datetime import datetime, date, time, timedelta
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.domain import User, Appointment, Branch, Service, Sector, Organization, Counter, QueueToken, QueueEvent, AppointmentReminder
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AvailableSlot, AppointmentReschedule, AppointmentReminderResponse
from app.services.token_service import issue_queue_token
from app.services.reminder_service import schedule_appointment_reminders, cancel_appointment_reminders, reschedule_appointment_reminders, process_due_reminders
from app.services.email_reminder_service import schedule_email_reminders, cancel_email_reminders, reschedule_email_reminders, process_due_email_reminders

router = APIRouter()

@router.get("/available-slots", response_model=List[time])
def get_available_slots(
    branch_id: UUID,
    service_id: UUID,
    appointment_date: date,
    db: Session = Depends(get_db)
):
    if appointment_date < date.today():
        return []

    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.status == 'ACTIVE').first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found or inactive")
        
    service = db.query(Service).filter(Service.id == service_id, Service.status == 'ACTIVE').first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found or inactive")
        
    # Determine branch capacity (Number of counters, default to 1 if none)
    counter_count = db.query(Counter).filter(Counter.branch_id == branch_id).count()
    capacity = max(1, counter_count)

    # Branch hours
    open_t = branch.opening_time or time(9, 0)
    close_t = branch.closing_time or time(17, 0)
    
    service_duration = service.average_service_time + (service.buffer_time or 0)
    if service_duration <= 0:
        service_duration = 15 # fallback

    # Generate potential slots
    slots = []
    current_dt = datetime.combine(appointment_date, open_t)
    end_dt = datetime.combine(appointment_date, close_t)
    
    # If checking today, don't return slots in the past
    now = datetime.now()
    if appointment_date == now.date():
        # push current_dt to next available interval
        while current_dt < now:
            current_dt += timedelta(minutes=service_duration)

    while current_dt + timedelta(minutes=service_duration) <= end_dt:
        slots.append(current_dt.time())
        current_dt += timedelta(minutes=service_duration)
        
    # Get existing appointments
    existing_apps = db.query(Appointment.appointment_time, func.count(Appointment.id).label('count')).filter(
        Appointment.branch_id == branch_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status.notin_(['CANCELLED'])
    ).group_by(Appointment.appointment_time).all()
    
    booked_counts = {app.appointment_time: app.count for app in existing_apps}
    
    available_slots = []
    for s in slots:
        if booked_counts.get(s, 0) < capacity:
            available_slots.append(s)

    return available_slots

@router.post("", response_model=AppointmentResponse)
def create_appointment(
    app_in: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if app_in.appointment_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot book in the past")

    # Validate relationships & status
    sector = db.query(Sector).filter(Sector.id == app_in.sector_id, Sector.status == 'ACTIVE').first()
    org = db.query(Organization).filter(Organization.id == app_in.organization_id, Organization.sector_id == app_in.sector_id, Organization.status == 'ACTIVE').first()
    branch = db.query(Branch).filter(Branch.id == app_in.branch_id, Branch.organization_id == app_in.organization_id, Branch.status == 'ACTIVE').first()
    service = db.query(Service).filter(Service.id == app_in.service_id, Service.sector_id == app_in.sector_id, Service.status == 'ACTIVE').first()
    
    if not (sector and org and branch and service):
        raise HTTPException(status_code=400, detail="Invalid or inactive sector/organization/branch/service combination")

    # Check user conflict
    conflict = db.query(Appointment).filter(
        Appointment.user_id == current_user.id,
        Appointment.appointment_date == app_in.appointment_date,
        Appointment.appointment_time == app_in.appointment_time,
        Appointment.status.notin_(['CANCELLED'])
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="You already have an appointment at this time.")

    # Concurrency protection & Capacity check
    # We use SERIALIZABLE isolation or row locking.
    # A simple approach is checking capacity, but to prevent race conditions we should lock the branch row temporarily
    # or just rely on a double check.
    
    # We lock the branch row to prevent concurrent bookings from exceeding capacity simultaneously for this specific branch
    if db.bind.dialect.name == "postgresql":
        db.execute(text(f"SELECT id FROM branches WHERE id = '{branch.id}' FOR UPDATE"))
    
    counter_count = db.query(Counter).filter(Counter.branch_id == branch.id).count()
    capacity = max(1, counter_count)
    
    current_bookings = db.query(Appointment).filter(
        Appointment.branch_id == branch.id,
        Appointment.appointment_date == app_in.appointment_date,
        Appointment.appointment_time == app_in.appointment_time,
        Appointment.status.notin_(['CANCELLED'])
    ).count()
    
    if current_bookings >= capacity:
        db.rollback()
        raise HTTPException(status_code=409, detail="This slot is no longer available. Please select another slot.")
        
    new_app = Appointment(
        user_id=current_user.id,
        sector_id=app_in.sector_id,
        organization_id=app_in.organization_id,
        branch_id=app_in.branch_id,
        service_id=app_in.service_id,
        appointment_date=app_in.appointment_date,
        appointment_time=app_in.appointment_time,
        status="BOOKED",
        notes=app_in.notes
    )
    
    db.add(new_app)
    db.flush()
    db.refresh(new_app)

    # Issue queue token and QR token in the same transaction
    token = issue_queue_token(db, new_app, current_user.id)

    # Step 9: Proactive Booking Notification & Real-time Live Branch Update
    try:
        from app.services.notification_service import notify_appointment_booked
        from app.services.broadcaster import broadcaster
        notify_appointment_booked(db, new_app, service, branch)
        broadcaster.broadcast_sync_branch(str(branch.id), {
            "event": "QUEUE_UPDATED",
            "action": "appointment_booked",
            "appointment_id": str(new_app.id),
            "token_id": str(token.id) if token else None
        })
    except Exception:
        pass

    # Schedule durable smart appointment reminders (in-app: T-120..30 & email: TWO_HOUR, THIRTY_MINUTE)
    try:
        schedule_appointment_reminders(db, new_app)
        schedule_email_reminders(db, new_app)
    except Exception:
        pass

    db.commit()
    db.refresh(new_app)
    
    # Format response
    resp = AppointmentResponse.model_validate(new_app)
    resp.sector_name = sector.name
    resp.organization_name = org.name
    resp.branch_name = f"{branch.address}, {branch.city}"
    resp.service_name = service.name
    if token:
        resp.token_number = token.token_number
        resp.queue_token_id = token.id
        resp.queue_position = token.queue_position
        resp.estimated_waiting_time = token.estimated_waiting_time
    
    return resp

@router.get("/user", response_model=List[AppointmentResponse])
def get_user_appointments(
    status: Optional[str] = Query(None, description="Filter by status (default BOOKED)"),
    include_completed: bool = Query(False, description="Include completed appointments in the response"),
    include_expired: bool = Query(False, description="Include expired appointments in the response"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_ids = [current_user.id]
    customer_pid = getattr(current_user, 'customer_profile_id', None)
    if customer_pid and customer_pid not in user_ids:
        user_ids.append(customer_pid)

    query = db.query(Appointment).options(
        joinedload(Appointment.sector),
        joinedload(Appointment.organization),
        joinedload(Appointment.branch),
        joinedload(Appointment.service)
    ).filter(
        Appointment.user_id.in_(user_ids)
    )

    # 1. Authoritative Status Filter:
    # An appointment should appear only if its status is strictly BOOKED.
    # Exclude CANCELLED, COMPLETED, NO_SHOW, SKIPPED, and any other non-BOOKED statuses.
    if include_completed:
        query = query.filter(Appointment.status != 'CANCELLED')
    elif status:
        query = query.filter(Appointment.status == status)
    else:
        query = query.filter(Appointment.status == 'BOOKED')

    # 2. Authoritative Expiry Date/Time Filter:
    # Scheduled appointment date and time must be >= current time in local timezone.
    if not include_expired and not include_completed:
        now_dt = datetime.now()
        now_date = now_dt.date()
        now_time = now_dt.time().replace(microsecond=0)

        query = query.filter(
            or_(
                Appointment.appointment_date > now_date,
                and_(
                    Appointment.appointment_date == now_date,
                    Appointment.appointment_time >= now_time
                )
            )
        )

    apps = query.order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc()).all()
    
    app_ids = [app.id for app in apps]
    tokens = {
        t.appointment_id: t 
        for t in db.query(QueueToken).filter(QueueToken.appointment_id.in_(app_ids)).all()
    } if app_ids else {}

    result = []
    has_new_tokens = False
    for app in apps:
        token = tokens.get(app.id)
        if not include_completed and token and token.status in ('COMPLETED', 'CANCELLED', 'NO_SHOW', 'SKIPPED'):
            continue

        if not token and app.status == 'BOOKED':
            token = issue_queue_token(db, app, current_user.id)
            tokens[app.id] = token
            has_new_tokens = True

        resp = AppointmentResponse.model_validate(app)
        resp.sector_name = app.sector.name if app.sector else "Unknown"
        resp.organization_name = app.organization.name if app.organization else "Unknown"
        resp.branch_name = f"{app.branch.address}, {app.branch.city}" if app.branch else "Unknown"
        resp.service_name = app.service.name if app.service else "Unknown"
        if token:
            resp.token_number = token.token_number
            resp.queue_token_id = token.id
            resp.queue_position = token.queue_position
            resp.estimated_waiting_time = token.estimated_waiting_time
        result.append(resp)
        
    if has_new_tokens:
        db.commit()

    return result

@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Appointment).options(
        joinedload(Appointment.sector),
        joinedload(Appointment.organization),
        joinedload(Appointment.branch),
        joinedload(Appointment.service)
    ).filter(Appointment.id == appointment_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    user_ids = [current_user.id]
    customer_pid = getattr(current_user, 'customer_profile_id', None)
    if customer_pid and customer_pid not in user_ids:
        user_ids.append(customer_pid)

    if app.user_id not in user_ids and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized to view this appointment")
        
    token = db.query(QueueToken).filter(QueueToken.appointment_id == app.id).first()

    resp = AppointmentResponse.model_validate(app)
    resp.sector_name = app.sector.name if app.sector else "Unknown"
    resp.organization_name = app.organization.name if app.organization else "Unknown"
    resp.branch_name = f"{app.branch.address}, {app.branch.city}" if app.branch else "Unknown"
    resp.service_name = app.service.name if app.service else "Unknown"
    if token:
        resp.token_number = token.token_number
        resp.queue_token_id = token.id
        resp.queue_position = token.queue_position
        resp.estimated_waiting_time = token.estimated_waiting_time
    
    return resp

@router.post("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    user_ids = [current_user.id]
    customer_pid = getattr(current_user, 'customer_profile_id', None)
    if customer_pid and customer_pid not in user_ids:
        user_ids.append(customer_pid)

    if app.user_id not in user_ids and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this appointment")
        
    if app.status in ['COMPLETED', 'SERVING']:
        raise HTTPException(status_code=409, detail=f"Cannot cancel appointment in {app.status} status")

    token = db.query(QueueToken).filter(QueueToken.appointment_id == appointment_id).first()
    if token and token.status in ['SERVING', 'COMPLETED']:
        raise HTTPException(status_code=409, detail="Cannot cancel appointment after service has started")

    if app.status == 'CANCELLED':
        raise HTTPException(status_code=409, detail="Appointment is already CANCELLED")
        
    app.status = 'CANCELLED'
    if token:
        prev_status = token.status
        token.status = 'CANCELLED'
        token.queue_position = None
        event = QueueEvent(
            token_id=token.id,
            event_type='CANCELLED',
            previous_status=prev_status,
            new_status='CANCELLED',
            counter_id=token.counter_id,
            performed_by=current_user.id,
            metadata_={"action": "cancel_appointment"}
        )
        db.add(event)

    # Step 9: Proactive Cancellation Notification & Real-time Live Branch Update
    try:
        from app.services.notification_service import notify_appointment_cancelled
        from app.services.broadcaster import broadcaster
        notify_appointment_cancelled(db, app, token)
        if app.branch_id:
            broadcaster.broadcast_sync_branch(str(app.branch_id), {
                "event": "QUEUE_UPDATED",
                "action": "appointment_cancelled",
                "appointment_id": str(app.id),
                "token_id": str(token.id) if token else None
            })
    except Exception:
        pass

    # Cancel pending reminders (in-app + email)
    try:
        cancel_appointment_reminders(db, app.id)
        cancel_email_reminders(db, app.id)
    except Exception:
        pass

    db.commit()
    
    return {"message": "Appointment cancelled successfully"}

@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: UUID,
    reschedule_in: AppointmentReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    user_ids = [current_user.id]
    customer_pid = getattr(current_user, 'customer_profile_id', None)
    if customer_pid and customer_pid not in user_ids:
        user_ids.append(customer_pid)

    if app.user_id not in user_ids and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized to reschedule this appointment")
        
    if app.status != "BOOKED":
        raise HTTPException(status_code=409, detail=f"Cannot reschedule appointment in {app.status} status")

    if reschedule_in.appointment_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot reschedule to a past date")

    app.appointment_date = reschedule_in.appointment_date
    app.appointment_time = reschedule_in.appointment_time
    if reschedule_in.notes is not None:
        app.notes = reschedule_in.notes
    db.flush()

    # Recalculate reminders and invalidate obsolete pending reminders
    try:
        reschedule_appointment_reminders(db, app)
        reschedule_email_reminders(db, app)
    except Exception:
        pass

    db.commit()
    db.refresh(app)

    token = db.query(QueueToken).filter(QueueToken.appointment_id == app.id).first()
    resp = AppointmentResponse.model_validate(app)
    if token:
        resp.token_number = token.token_number
        resp.queue_token_id = token.id
        resp.queue_position = token.queue_position
        resp.estimated_waiting_time = token.estimated_waiting_time
    return resp

@router.get("/{appointment_id}/reminders", response_model=List[AppointmentReminderResponse])
def get_appointment_reminders(
    appointment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    user_ids = [current_user.id]
    customer_pid = getattr(current_user, 'customer_profile_id', None)
    if customer_pid and customer_pid not in user_ids:
        user_ids.append(customer_pid)

    if app.user_id not in user_ids and current_user.role not in ['ADMIN', 'STAFF']:
        raise HTTPException(status_code=403, detail="Not authorized to view reminders for this appointment")
        
    reminders = db.query(AppointmentReminder).filter(
        AppointmentReminder.appointment_id == appointment_id
    ).order_by(AppointmentReminder.minutes_before.desc()).all()
    return reminders

@router.post("/reminders/process-due")
def trigger_process_due_reminders(
    reference_time: Optional[str] = Query(None, description="ISO timestamp for testing/reference time"),
    db: Session = Depends(get_db)
):
    ref_dt = None
    if reference_time:
        try:
            ref_dt = datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid reference_time format. Use ISO format.")
    in_app_stats = process_due_reminders(db, reference_now_utc=ref_dt)
    email_stats = process_due_email_reminders(db, reference_now_utc=ref_dt)
    return {
        "checked_reminders": in_app_stats.get("checked_reminders", 0) + email_stats.get("checked", 0),
        "processed": in_app_stats.get("processed", 0) + email_stats.get("sent", 0),
        "in_app": in_app_stats,
        "email": email_stats
    }

