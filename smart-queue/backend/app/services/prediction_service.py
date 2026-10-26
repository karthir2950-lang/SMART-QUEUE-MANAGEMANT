from datetime import datetime, timezone, timedelta, date, time
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.domain import Appointment, Branch, Service, Sector, Organization, QueueToken, Counter, QueueEvent
from app.schemas.notification import AIPredictionResponse
from app.services.token_service import calculate_precise_people_ahead

def calculate_ai_prediction(
    db: Session,
    token: QueueToken,
    appt: Appointment,
    service: Service,
    branch: Branch
) -> AIPredictionResponse:
    """
    Step 9 AI Dynamic Wait-Time Prediction Engine.
    Scales wait times dynamically using:
    1. Exact sequential queue position and people ahead.
    2. Active counter capacity (parallel throughput).
    3. Real-world handling velocity from today's completed tokens.
    4. Time-of-day peak congestion curve and no-show drop-off probabilities.
    """
    people_ahead = calculate_precise_people_ahead(db, token, appt)

    # 1. Active Counter Capacity (Parallel Throughput)
    active_counters_count = db.query(Counter).filter(
        Counter.branch_id == branch.id,
        Counter.status.in_(['AVAILABLE', 'BUSY'])
    ).count()
    effective_counters = max(1, active_counters_count)

    # 2. Real-Time Service Velocity Sampling
    nominal_service_minutes = float(service.average_service_time + (service.buffer_time or 0)) if service else 15.0

    today = appt.appointment_date or date.today()
    completed_today = (
        db.query(QueueToken)
        .join(Appointment, QueueToken.appointment_id == Appointment.id)
        .filter(
            Appointment.service_id == service.id,
            Appointment.appointment_date == today,
            QueueToken.status == 'COMPLETED',
            QueueToken.started_at.isnot(None),
            QueueToken.completed_at.isnot(None)
        )
        .limit(20)
        .all()
    )

    durations = []
    for tok in completed_today:
        if tok.started_at and tok.completed_at:
            dur_mins = (tok.completed_at - tok.started_at).total_seconds() / 60.0
            if 1.0 <= dur_mins <= 180.0:
                durations.append(dur_mins)

    if len(durations) >= 2:
        sampled_avg = sum(durations) / len(durations)
        # Weighted blend: 70% actual velocity + 30% baseline nominal
        dynamic_avg_handling = (sampled_avg * 0.70) + (nominal_service_minutes * 0.30)
    else:
        dynamic_avg_handling = nominal_service_minutes

    dynamic_avg_handling = max(2.0, dynamic_avg_handling)

    # 3. Peak Hour Factor
    now_hour = datetime.now(timezone.utc).hour
    if (10 <= now_hour <= 12) or (14 <= now_hour <= 16):
        congestion_multiplier = 1.12
    elif (12 < now_hour < 14):
        congestion_multiplier = 1.05
    else:
        congestion_multiplier = 0.95

    # 4. No-Show & Drop-off Probability Factor (~10% buffer reduction)
    drop_off_factor = 0.90

    # 5. Compute Predicted Wait Time
    if token.status in ['CALLED', 'SERVING']:
        predicted_wait = 0
        min_wait = 0
        max_wait = 2
        confidence = 99
        congestion_level = "LOW"
        turn_prob_15m = 100
        ai_msg = f"Token is currently {token.status}. Please be at your assigned service desk immediately."
    elif people_ahead == 0:
        predicted_wait = max(1, int(round(dynamic_avg_handling * 0.4)))
        min_wait = 0
        max_wait = max(2, int(round(dynamic_avg_handling * 0.8)))
        confidence = 96
        congestion_level = "LOW"
        turn_prob_15m = 95
        ai_msg = f"You are next in line! Only waiting for current desk to complete."
    else:
        raw_wait = (people_ahead * dynamic_avg_handling * congestion_multiplier * drop_off_factor) / effective_counters
        predicted_wait = max(1, int(round(raw_wait)))
        min_wait = max(1, int(round(predicted_wait * 0.80)))
        max_wait = int(round(predicted_wait * 1.25)) + 2

        # Confidence: declines slightly with deep queues
        confidence = max(70, min(95, int(95 - (people_ahead * 1.5) + (len(durations) * 1.2))))

        if people_ahead <= 2:
            congestion_level = "LOW"
            turn_prob_15m = 88
        elif people_ahead <= 6:
            congestion_level = "MODERATE"
            turn_prob_15m = 65
        elif people_ahead <= 12:
            congestion_level = "HIGH"
            turn_prob_15m = 35
        else:
            congestion_level = "PEAK"
            turn_prob_15m = 15

        ai_msg = (
            f"AI model factored {effective_counters} active service desk(s), {dynamic_avg_handling:.1f}m handling velocity, "
            f"and {people_ahead} customer(s) ahead with {congestion_level.lower()} traffic adjustment."
        )

    est_call_time = (datetime.now(timezone.utc) + timedelta(minutes=predicted_wait)).strftime("%H:%M UTC")

    return AIPredictionResponse(
        token_id=token.id,
        token_number=token.token_number,
        people_ahead=people_ahead,
        active_counters_count=active_counters_count,
        base_service_minutes=int(nominal_service_minutes),
        dynamic_avg_handling_minutes=round(dynamic_avg_handling, 1),
        predicted_wait_minutes=predicted_wait,
        min_wait_minutes=min_wait,
        max_wait_minutes=max_wait,
        confidence_score=confidence,
        congestion_level=congestion_level,
        turn_probability_next_15m=turn_prob_15m,
        estimated_call_time=est_call_time,
        ai_explanation=ai_msg
    )
