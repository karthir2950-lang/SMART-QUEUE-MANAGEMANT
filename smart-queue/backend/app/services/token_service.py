import uuid
from uuid import UUID
import secrets
import string
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, cast, Date

from app.models.domain import Appointment, Branch, Service, Sector, Organization, QueueToken, QueueEvent, QRToken, Counter
from app.schemas.queue import QueueTokenResponse

def get_token_prefix(sector_slug: str) -> str:
    slug = (sector_slug or '').lower()
    if 'hospital' in slug or 'health' in slug:
        return 'H'
    if 'bank' in slug or 'finance' in slug:
        return 'B'
    if 'restaurant' in slug or 'food' in slug:
        return 'R'
    if 'gov' in slug:
        return 'G'
    if 'retail' in slug:
        return 'RT'
    if 'supermarket' in slug:
        return 'SM'
    return 'T'

def generate_secure_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def calculate_precise_people_ahead(db: Session, token: QueueToken, appt: Appointment) -> int:
    try:
        query = db.query(QueueToken, Appointment).join(
            Appointment, QueueToken.appointment_id == Appointment.id
        ).filter(
            Appointment.branch_id == appt.branch_id,
            Appointment.service_id == appt.service_id,
            Appointment.appointment_date == appt.appointment_date,
            QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING']),
            QueueToken.id != token.id
        )
        all_active = query.all()
        ahead = 0
        for t, t_appt in all_active:
            if (t_appt.appointment_time < appt.appointment_time) or \
               (t_appt.appointment_time == appt.appointment_time and t.created_at < token.created_at) or \
               (t_appt.appointment_time == appt.appointment_time and t.created_at == token.created_at and str(t.id) < str(token.id)):
                ahead += 1
        return ahead
    except Exception:
        return 0

def get_next_token_number(db: Session, branch_id: UUID, prefix: str) -> str:
    """
    Safely calculates the next sequential token number for this branch and prefix today.
    Avoids unsafe COUNT(*) + 1 by inspecting maximum existing sequence numbers.
    """
    existing_tokens = db.query(QueueToken.token_number).join(
        Appointment, QueueToken.appointment_id == Appointment.id
    ).filter(
        Appointment.branch_id == branch_id,
        cast(QueueToken.created_at, Date) == date.today(),
        QueueToken.token_number.like(f"{prefix}-%")
    ).all()

    max_num = 0
    for (t_num,) in existing_tokens:
        if not t_num:
            continue
        try:
            suffix = t_num.split('-')[-1]
            val = int(suffix)
            if val > max_num:
                max_num = val
        except (ValueError, IndexError):
            continue

    next_num = max_num + 1
    return f"{prefix}-{next_num:03d}"

def issue_queue_token(
    db: Session,
    appointment: Appointment,
    user_id: UUID
) -> QueueToken:
    """
    Idempotent and concurrency-safe token generation.
    Reuses existing token if already issued for this appointment.
    Otherwise locks the branch row, generates a non-colliding sequential token,
    creates the queue event, and generates a linked QRToken.
    """
    # 1. Idempotency check: see if token already exists
    existing = db.query(QueueToken).filter(QueueToken.appointment_id == appointment.id).first()
    if existing:
        return existing

    sector = db.query(Sector).filter(Sector.id == appointment.sector_id).first()
    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    branch = db.query(Branch).filter(Branch.id == appointment.branch_id).first()

    prefix = get_token_prefix(sector.slug if sector else "token")

    # Lock the branch row in PostgreSQL to prevent concurrent race condition sequence collisions
    if db.bind and db.bind.dialect.name == "postgresql" and branch:
        try:
            db.execute(text(f"SELECT id FROM branches WHERE id = '{branch.id}' FOR UPDATE"))
        except Exception:
            pass

    # Double check after lock
    existing_after_lock = db.query(QueueToken).filter(QueueToken.appointment_id == appointment.id).first()
    if existing_after_lock:
        return existing_after_lock

    token_number = get_next_token_number(db, appointment.branch_id, prefix)

    new_token = QueueToken(
        id=uuid.uuid4(),
        appointment_id=appointment.id,
        token_number=token_number,
        status="WAITING",
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_token)
    db.flush()
    db.refresh(new_token)

    people_ahead = calculate_precise_people_ahead(db, new_token, appointment)
    avg_service = (service.average_service_time + (service.buffer_time or 0)) if service else 15
    new_token.queue_position = people_ahead + 1
    new_token.estimated_waiting_time = people_ahead * avg_service

    # Create Queue Event
    event = QueueEvent(
        token_id=new_token.id,
        event_type="TOKEN_CREATED",
        previous_status=None,
        new_status="WAITING",
        performed_by=user_id
    )
    db.add(event)

    # Create QR Token
    existing_qr = db.query(QRToken).filter(QRToken.appointment_id == appointment.id).first()
    if not existing_qr:
        qr = QRToken(
            appointment_id=appointment.id,
            queue_token_id=new_token.id,
            secure_token=generate_secure_token(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db.add(qr)

    # Step 9: Automated Notification Dispatch
    try:
        from app.services.notification_service import notify_token_generated
        notify_token_generated(db, new_token, appointment, service, branch)
    except Exception:
        pass

    db.flush()
    db.refresh(new_token)
    return new_token

def enrich_token_response(
    db: Session,
    token: QueueToken,
    appt: Appointment,
    service: Service,
    sector: Sector,
    org: Organization,
    branch: Branch
) -> QueueTokenResponse:
    if token.status in ['CALLED', 'SERVING']:
        people_ahead = 0
        est_wait = 0
    elif token.status in ['COMPLETED', 'CANCELLED']:
        people_ahead = 0
        est_wait = 0
    else:
        people_ahead = calculate_precise_people_ahead(db, token, appt)
        if service and service.average_service_time:
            avg_service = service.average_service_time + (service.buffer_time or 0)
            est_wait = people_ahead * avg_service
            try:
                if branch and service:
                    from app.services.prediction_service import calculate_ai_prediction
                    pred = calculate_ai_prediction(db, token, appt, service, branch)
                    est_wait = pred.predicted_wait_minutes
            except Exception:
                pass
        else:
            est_wait = None

    qr_token = db.query(QRToken).filter(QRToken.queue_token_id == token.id).first()

    # Query the real currently serving token at this specific branch & service today
    serving_query = db.query(QueueToken, Counter).join(
        Appointment, QueueToken.appointment_id == Appointment.id
    ).outerjoin(
        Counter, QueueToken.counter_id == Counter.id
    ).filter(
        Appointment.branch_id == appt.branch_id,
        Appointment.service_id == appt.service_id,
        Appointment.appointment_date == appt.appointment_date,
        QueueToken.status.in_(['SERVING', 'CALLED'])
    ).order_by(
        QueueToken.started_at.desc().nullslast(),
        QueueToken.called_at.desc().nullslast(),
        QueueToken.created_at.asc()
    ).first()

    currently_serving_num = None
    currently_serving_cnt = None
    if serving_query:
        s_tok, s_counter = serving_query
        currently_serving_num = s_tok.token_number
        if s_counter:
            currently_serving_cnt = f"Desk #{s_counter.counter_number} ({s_counter.name})"
        else:
            currently_serving_cnt = "Service Desk"

    resp = QueueTokenResponse.model_validate(token)
    resp.sector_name = sector.name if sector else "Unknown"
    resp.organization_name = org.name if org else "Unknown"
    resp.branch_name = f"{branch.address}, {branch.city}" if branch else "Unknown"
    resp.service_name = service.name if service else "Unknown"
    resp.appointment_date = appt.appointment_date
    resp.appointment_time = appt.appointment_time
    resp.people_ahead = people_ahead
    resp.estimated_waiting_time = est_wait
    resp.queue_position = (people_ahead + 1) if token.status == 'WAITING' else (1 if token.status in ['CALLED', 'SERVING'] else None)
    resp.currently_serving_token = currently_serving_num
    resp.currently_serving_counter = currently_serving_cnt
    resp.server_time = datetime.now(timezone.utc)

    if qr_token:
        resp.qr_secure_token = qr_token.secure_token
    return resp
