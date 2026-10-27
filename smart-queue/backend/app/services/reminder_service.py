import uuid
import logging
from uuid import UUID
from datetime import datetime, timezone, timedelta, date, time
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.domain import Appointment, AppointmentReminder, Notification, QueueToken, Branch, Service, User
from app.services.notification_service import create_user_notification

logger = logging.getLogger(__name__)

# Standard reminder intervals before appointment (in minutes)
REMINDER_INTERVALS = [120, 90, 60, 30]

DEFAULT_TIMEZONE = "Asia/Kolkata"

def resolve_timezone(tz_name: str = DEFAULT_TIMEZONE):
    """
    Resolves IANA timezone name with fallback to fixed UTC+5:30 offset for Asia/Kolkata.
    """
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        if tz_name in ("Asia/Kolkata", "IST"):
            return timezone(timedelta(hours=5, minutes=30))
        return timezone.utc

def get_appointment_target_datetime(appt: Appointment, tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    """
    Combines appointment_date and appointment_time into a timezone-aware UTC datetime.
    Defaults to Asia/Kolkata (IST).
    """
    tz = resolve_timezone(tz_name)

    # Ensure appointment_time is a time object
    a_time = appt.appointment_time
    if isinstance(a_time, str):
        # Format HH:MM:SS or HH:MM
        parts = [int(p) for p in a_time.split(":")[:3]]
        if len(parts) == 2:
            a_time = time(parts[0], parts[1])
        elif len(parts) == 3:
            a_time = time(parts[0], parts[1], parts[2])

    a_date = appt.appointment_date
    if isinstance(a_date, str):
        a_date = date.fromisoformat(a_date)

    local_dt = datetime.combine(a_date, a_time, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def calculate_future_reminder_times(
    appt: Appointment,
    current_utc: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> List[Dict[str, Any]]:
    """
    Calculates valid future reminder timestamps for an appointment.
    Rules:
    - First reminder: exactly 120 minutes (2 hours) before appointment.
    - Subsequent reminders: 90, 60, and 30 minutes before appointment.
    - If booked less than 2 hours before, DO NOT send overdue reminders.
      Schedule only future reminder times that occur strictly before the appointment.
    - If current_utc >= appointment_time, schedule NO reminders.
    """
    if current_utc is None:
        current_utc = datetime.now(timezone.utc)

    appt_utc = get_appointment_target_datetime(appt, tz_name)

    # If the appointment time has already arrived or passed, no reminders can be scheduled
    if current_utc >= appt_utc:
        return []

    valid_schedules = []
    for minutes in REMINDER_INTERVALS:
        reminder_time = appt_utc - timedelta(minutes=minutes)

        # The reminder time must be strictly in the future relative to current_utc
        # AND strictly before the appointment time
        if reminder_time > current_utc and reminder_time < appt_utc:
            valid_schedules.append({
                "reminder_type": f"T_MINUS_{minutes}",
                "minutes_before": minutes,
                "scheduled_for": reminder_time
            })

    return valid_schedules


def schedule_appointment_reminders(
    db: Session,
    appt: Appointment,
    current_utc: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> List[AppointmentReminder]:
    """
    Persists durable appointment reminder schedules in the database.
    Idempotent: Uses unique (appointment_id, reminder_type) constraints.
    """
    if not appt or appt.status != "BOOKED":
        return []

    schedules = calculate_future_reminder_times(appt, current_utc=current_utc, tz_name=tz_name)
    if not schedules:
        return []

    created_or_updated = []
    for s in schedules:
        # Check if already exists
        existing = db.query(AppointmentReminder).filter(
            AppointmentReminder.appointment_id == appt.id,
            AppointmentReminder.reminder_type == s["reminder_type"]
        ).first()

        if existing:
            if existing.status in ("CANCELLED", "PROCESSED", "SKIPPED") or existing.scheduled_for != s["scheduled_for"]:
                existing.status = "PENDING"
                existing.scheduled_for = s["scheduled_for"]
                existing.notification_id = None
                existing.processed_at = None
                existing.updated_at = datetime.now(timezone.utc)
            created_or_updated.append(existing)
        else:
            reminder = AppointmentReminder(
                id=uuid.uuid4(),
                appointment_id=appt.id,
                user_id=appt.user_id,
                reminder_type=s["reminder_type"],
                minutes_before=s["minutes_before"],
                scheduled_for=s["scheduled_for"],
                status="PENDING"
            )
            db.add(reminder)
            created_or_updated.append(reminder)

    db.flush()
    return created_or_updated


def cancel_appointment_reminders(db: Session, appointment_id: UUID) -> int:
    """
    Cancels all pending reminders for an appointment when it is cancelled, completed, or no-show.
    """
    count = db.query(AppointmentReminder).filter(
        AppointmentReminder.appointment_id == appointment_id,
        AppointmentReminder.status == "PENDING"
    ).update({"status": "CANCELLED"}, synchronize_session=False)
    db.flush()
    return count


def reschedule_appointment_reminders(
    db: Session,
    appt: Appointment,
    current_utc: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> List[AppointmentReminder]:
    """
    Cancels obsolete reminders and generates new future schedules for a rescheduled appointment.
    """
    cancel_appointment_reminders(db, appt.id)
    return schedule_appointment_reminders(db, appt, current_utc=current_utc, tz_name=tz_name)


def format_remaining_label(minutes_before: int) -> str:
    if minutes_before == 120:
        return "in 2 hours"
    elif minutes_before == 60:
        return "in 1 hour"
    else:
        return f"in {minutes_before} minutes"


def process_due_reminders(
    db: Session,
    reference_now_utc: Optional[datetime] = None,
    appointment_id: Optional[UUID] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> Dict[str, Any]:
    """
    Processes all due reminders (scheduled_for <= now_utc and status == 'PENDING').
    Performs Phase 4 authoritative eligibility checks:
    - Appointment exists and status is strictly BOOKED.
    - Token (if present) is not CANCELLED, COMPLETED, NO_SHOW, or SKIPPED.
    - Current time is strictly earlier than scheduled appointment time.
    - Deduplication: Never dispatches duplicate notification.
    """
    now_utc = reference_now_utc or datetime.now(timezone.utc)

    # Query due reminders with row-level locking where supported
    query = db.query(AppointmentReminder).filter(
        AppointmentReminder.status == "PENDING",
        AppointmentReminder.scheduled_for <= now_utc
    )
    if appointment_id:
        query = query.filter(AppointmentReminder.appointment_id == appointment_id)

    if db.bind and db.bind.dialect.name == "postgresql":
        try:
            query = query.with_for_update(skip_locked=True)
        except Exception:
            pass

    due_reminders = query.all()

    processed_count = 0
    cancelled_count = 0
    skipped_count = 0
    errors_count = 0

    for rem in due_reminders:
        try:
            # 1. Fetch appointment with related entities
            appt = db.query(Appointment).options(
                joinedload(Appointment.service),
                joinedload(Appointment.branch)
            ).filter(Appointment.id == rem.appointment_id).first()

            # Check 1: Appointment exists and belongs to intended user
            if not appt or str(appt.user_id) != str(rem.user_id):
                rem.status = "CANCELLED"
                rem.updated_at = now_utc
                cancelled_count += 1
                db.commit()
                continue

            # Check 2: Appointment status must be strictly BOOKED
            if appt.status != "BOOKED":
                rem.status = "CANCELLED"
                rem.updated_at = now_utc
                cancelled_count += 1
                db.commit()
                continue

            # Check 3: Check QueueToken status if issued
            token = db.query(QueueToken).filter(QueueToken.appointment_id == appt.id).first()
            if token and token.status in ["CANCELLED", "COMPLETED", "NO_SHOW", "SKIPPED"]:
                rem.status = "CANCELLED"
                rem.updated_at = now_utc
                cancelled_count += 1
                db.commit()
                continue

            # Check 4: Current time strictly earlier than scheduled appointment time
            appt_utc = get_appointment_target_datetime(appt, tz_name)
            if now_utc >= appt_utc:
                # Reached or passed scheduled appointment time: NEVER send reminder at or after T
                rem.status = "SKIPPED"
                rem.updated_at = now_utc
                skipped_count += 1
                db.commit()
                continue

            # Check 5: Idempotency check against notifications table
            # Check if an APPOINTMENT_REMINDER was already created for this specific reminder
            existing_notif = db.query(Notification).filter(
                Notification.user_id == appt.user_id,
                Notification.appointment_id == appt.id,
                Notification.type == "APPOINTMENT_REMINDER",
                or_(
                    Notification.title.ilike(f"%{rem.minutes_before} minutes%"),
                    Notification.title.ilike(f"%{format_remaining_label(rem.minutes_before)}%")
                )
            ).first()

            if existing_notif:
                rem.status = "PROCESSED"
                rem.notification_id = existing_notif.id
                rem.processed_at = existing_notif.created_at or now_utc
                rem.updated_at = now_utc
                db.commit()
                continue

            # Phase 5: Notification Delivery
            remaining_str = format_remaining_label(rem.minutes_before)
            svc_name = appt.service.name if appt.service else "Service"
            branch_name = f"{appt.branch.address}, {appt.branch.city}" if appt.branch else "Branch"

            tz = resolve_timezone(tz_name)
            local_dt = appt_utc.astimezone(tz)
            date_str = local_dt.strftime("%A, %d %B %Y")
            time_str = local_dt.strftime("%I:%M %p")

            title = f"⏰ Upcoming Appointment {remaining_str}: {svc_name}"
            message = (
                f"Reminder: Your appointment for {svc_name} at {branch_name} is scheduled for "
                f"{date_str} at {time_str} ({remaining_str}). Please arrive a few minutes early."
            )

            notif = create_user_notification(
                db=db,
                user_id=appt.user_id,
                n_type="APPOINTMENT_REMINDER",
                title=title,
                message=message,
                appointment_id=appt.id
            )

            rem.status = "PROCESSED"
            rem.notification_id = notif.id
            rem.processed_at = now_utc
            rem.updated_at = now_utc
            db.commit()
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing reminder {rem.id}: {e}")
            db.rollback()
            errors_count += 1

    return {
        "checked_reminders": len(due_reminders),
        "processed": processed_count,
        "cancelled": cancelled_count,
        "skipped": skipped_count,
        "errors": errors_count
    }
