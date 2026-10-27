import uuid
import logging
from uuid import UUID
from datetime import datetime, timezone, timedelta, date, time
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.models.domain import Appointment, AppointmentReminder, QueueToken, Branch, Service, Organization, User
from app.services.reminder_service import get_appointment_target_datetime, resolve_timezone, DEFAULT_TIMEZONE
from app.services.email_service import send_appointment_reminder_email, is_valid_email

logger = logging.getLogger(__name__)

# Two distinct reminder events specified by QueueLess AI Phase 2 & Phase 4
EMAIL_REMINDER_EVENTS = [
    {
        "reminder_type": "EMAIL_TWO_HOUR",
        "alias": "TWO_HOUR",
        "minutes_before": 120,
        "remaining_label": "in 2 hours"
    },
    {
        "reminder_type": "EMAIL_THIRTY_MINUTE",
        "alias": "THIRTY_MINUTE",
        "minutes_before": 30,
        "remaining_label": "in 30 minutes"
    }
]

def calculate_email_reminder_times(
    appt: Appointment,
    current_utc: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> List[Dict[str, Any]]:
    """
    Calculates eligible future email reminder schedules for an appointment:
    - First reminder: exactly 2 hours (120 mins) before appointment (TWO_HOUR)
    - Second reminder: exactly 30 minutes before appointment (THIRTY_MINUTE)
    
    Rules:
    1. If appointment is > 2 hours away, both reminders are scheduled.
    2. If booked between 2 hours and 30 minutes before, skip the first reminder 
       (if its scheduled time has already passed) and schedule the 30-minute reminder only.
    3. If booked 30 minutes or less before, schedule NO reminders (no overdue alerts).
    4. Never schedule any reminder at or after appointment time T.
    """
    if current_utc is None:
        current_utc = datetime.now(timezone.utc)

    appt_utc = get_appointment_target_datetime(appt, tz_name)

    # Hard cutoff: If appointment time has already arrived or passed, no reminders
    if current_utc >= appt_utc:
        return []

    valid_schedules = []
    for event in EMAIL_REMINDER_EVENTS:
        minutes = event["minutes_before"]
        reminder_time = appt_utc - timedelta(minutes=minutes)

        # Reminder must be strictly in the future relative to current_utc
        # AND strictly earlier than appointment time appt_utc
        if reminder_time > current_utc and reminder_time < appt_utc:
            valid_schedules.append({
                "reminder_type": event["reminder_type"],
                "alias": event["alias"],
                "minutes_before": minutes,
                "scheduled_for": reminder_time,
                "remaining_label": event["remaining_label"]
            })

    return valid_schedules


def schedule_email_reminders(
    db: Session,
    appt: Appointment,
    current_utc: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> List[AppointmentReminder]:
    """
    Persists durable database-backed email reminder schedules in public.appointment_reminders.
    Idempotent: Uses unique (appointment_id, reminder_type) database constraint.
    """
    if not appt or appt.status != "BOOKED":
        return []

    schedules = calculate_email_reminder_times(appt, current_utc=current_utc, tz_name=tz_name)
    if not schedules:
        return []

    persisted = []
    for s in schedules:
        # Check existing record by primary or alias reminder_type
        existing = db.query(AppointmentReminder).filter(
            AppointmentReminder.appointment_id == appt.id,
            or_(
                AppointmentReminder.reminder_type == s["reminder_type"],
                AppointmentReminder.reminder_type == s["alias"]
            )
        ).first()

        if existing:
            if existing.status in ("CANCELLED", "SENT", "FAILED", "SKIPPED") or existing.scheduled_for != s["scheduled_for"]:
                existing.status = "PENDING"
                existing.scheduled_for = s["scheduled_for"]
                existing.processed_at = None
                existing.updated_at = datetime.now(timezone.utc)
            persisted.append(existing)
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
            persisted.append(reminder)

    db.flush()
    return persisted


def cancel_email_reminders(db: Session, appointment_id: UUID) -> int:
    """
    Cancels all pending email reminders for an appointment when cancelled, completed, skipped, or no-show.
    """
    count = db.query(AppointmentReminder).filter(
        AppointmentReminder.appointment_id == appointment_id,
        AppointmentReminder.status == "PENDING",
        AppointmentReminder.reminder_type.in_(["EMAIL_TWO_HOUR", "EMAIL_THIRTY_MINUTE", "TWO_HOUR", "THIRTY_MINUTE"])
    ).update({"status": "CANCELLED"}, synchronize_session=False)
    db.flush()
    return count


def reschedule_email_reminders(
    db: Session,
    appt: Appointment,
    current_utc: Optional[datetime] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> List[AppointmentReminder]:
    """
    Cancels obsolete email reminders and calculates new valid schedules for rescheduled appointment.
    """
    cancel_email_reminders(db, appt.id)
    return schedule_email_reminders(db, appt, current_utc=current_utc, tz_name=tz_name)


def process_due_email_reminders(
    db: Session,
    reference_now_utc: Optional[datetime] = None,
    appointment_id: Optional[UUID] = None,
    tz_name: str = DEFAULT_TIMEZONE
) -> Dict[str, Any]:
    """
    Processes due email reminders (scheduled_for <= now_utc and status == 'PENDING').
    
    Authoritative Eligibility Checks Before Dispatch:
    1. Appointment still exists and belongs to intended user.
    2. Appointment status is strictly BOOKED.
    3. Token (if issued) is not CANCELLED, COMPLETED, NO_SHOW, or SKIPPED.
    4. Current time is strictly earlier than scheduled appointment time (now_utc < T).
    5. Overdue check: If a reminder job runs late and appointment time has passed, skip rather than send late.
    6. Recipient address must be verified from trusted user profile.
    7. Idempotency: Double execution will find status already 'SENT' or row locked.
    """
    now_utc = reference_now_utc or datetime.now(timezone.utc)

    query = db.query(AppointmentReminder).filter(
        AppointmentReminder.status == "PENDING",
        AppointmentReminder.scheduled_for <= now_utc,
        AppointmentReminder.reminder_type.in_(["EMAIL_TWO_HOUR", "EMAIL_THIRTY_MINUTE", "TWO_HOUR", "THIRTY_MINUTE"])
    )
    if appointment_id:
        query = query.filter(AppointmentReminder.appointment_id == appointment_id)

    # Concurrency safe: with_for_update(skip_locked=True)
    if db.bind and db.bind.dialect.name == "postgresql":
        try:
            query = query.with_for_update(skip_locked=True)
        except Exception:
            pass

    due_reminders = query.all()

    sent_count = 0
    cancelled_count = 0
    skipped_count = 0
    failed_count = 0

    for rem in due_reminders:
        try:
            # 1. Fetch appointment with related entities
            appt = db.query(Appointment).options(
                joinedload(Appointment.service),
                joinedload(Appointment.branch),
                joinedload(Appointment.user)
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

            # Check 4: Strict Cutoff - Never send reminder at or after appointment time T
            appt_utc = get_appointment_target_datetime(appt, tz_name)
            if now_utc >= appt_utc:
                rem.status = "SKIPPED"
                rem.updated_at = now_utc
                skipped_count += 1
                db.commit()
                continue

            # Check 5: Recipient email verification
            user = appt.user or db.query(User).filter(User.id == appt.user_id).first()
            recipient_email = user.email if user else None
            if not recipient_email or not is_valid_email(recipient_email):
                logger.warning(f"Reminder skipped: No valid verified email for user {rem.user_id}")
                rem.status = "FAILED"
                rem.updated_at = now_utc
                failed_count += 1
                db.commit()
                continue

            # Format localized display strings
            tz = resolve_timezone(tz_name)
            local_dt = appt_utc.astimezone(tz)
            date_str = local_dt.strftime("%A, %d %B %Y")
            time_str = local_dt.strftime("%I:%M %p")
            
            user_display_name = user.name if user and user.name else recipient_email.split("@")[0].title()
            service_name = appt.service.name if appt.service else "Service"
            org_name = appt.organization.name if hasattr(appt, "organization") and appt.organization else "Organization"
            branch_name = f"{appt.branch.address}, {appt.branch.city}" if appt.branch else "Branch"
            token_number = token.token_number if token else None

            remaining_label = "in 2 hours" if rem.minutes_before == 120 else "in 30 minutes"

            # Dispatch Transactional Email
            delivery_res = send_appointment_reminder_email(
                recipient_email=recipient_email,
                user_name=user_display_name,
                service_name=service_name,
                organization_name=org_name,
                branch_name=branch_name,
                date_str=date_str,
                time_str=time_str,
                remaining_label=remaining_label,
                token_number=token_number,
                appointment_id=str(appt.id),
                reminder_type=rem.reminder_type
            )

            if delivery_res.get("success"):
                rem.status = "SENT"
                rem.processed_at = now_utc
                rem.updated_at = now_utc
                db.commit()
                sent_count += 1
            else:
                rem.status = "FAILED"
                rem.updated_at = now_utc
                db.commit()
                failed_count += 1

        except Exception as e:
            logger.error(f"Error processing email reminder {rem.id}: {e}")
            db.rollback()
            failed_count += 1

    return {
        "checked": len(due_reminders),
        "sent": sent_count,
        "cancelled": cancelled_count,
        "skipped": skipped_count,
        "failed": failed_count
    }
