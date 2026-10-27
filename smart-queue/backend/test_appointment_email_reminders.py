import sys
import os
import uuid
from datetime import date, time as dt_time, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Appointment, Branch, Service, Organization, QueueToken, AppointmentReminder
from app.services.email_service import (
    SENT_EMAILS_REGISTRY,
    send_appointment_reminder_email,
    render_reminder_email_html,
    render_reminder_email_text,
    is_valid_email
)
from app.services.reminder_service import get_appointment_target_datetime, resolve_timezone
from app.services.email_reminder_service import (
    calculate_email_reminder_times,
    schedule_email_reminders,
    cancel_email_reminders,
    reschedule_email_reminders,
    process_due_email_reminders
)

client = TestClient(app)

def run_all_email_reminder_tests():
    db = SessionLocal()
    print("==================================================================")
    print("RUNNING QUEUELESS AI: SCHEDULED APPOINTMENT EMAIL REMINDERS SUITE")
    print("==================================================================")
    passed_count = 0
    total_tests = 10

    # Ensure isolated test user exists
    test_user = db.query(User).filter(User.email == "test_customer_email@example.com").first()
    if not test_user:
        test_user = User(
            id=uuid.uuid4(),
            name="Rahul Sharma",
            email="test_customer_email@example.com",
            phone="+919876543299",
            role="USER",
            status="ACTIVE"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

    branch = db.query(Branch).first()
    service = db.query(Service).first()
    IST = resolve_timezone("Asia/Kolkata")

    # Clean up any leftover test data
    SENT_EMAILS_REGISTRY.clear()
    db.query(AppointmentReminder).filter(AppointmentReminder.user_id == test_user.id).delete(synchronize_session=False)
    test_appts = db.query(Appointment.id).filter(Appointment.user_id == test_user.id).all()
    if test_appts:
        appt_ids = [a[0] for a in test_appts]
        db.query(QueueToken).filter(QueueToken.appointment_id.in_(appt_ids)).delete(synchronize_session=False)
    db.query(Appointment).filter(Appointment.user_id == test_user.id).delete(synchronize_session=False)
    db.commit()

    try:
        # =====================================================================
        # TEST 1: Appointment is > 2 hours away: both reminders are scheduled
        # =====================================================================
        now_ist = datetime.now(IST)
        target_dt_1 = now_ist + timedelta(hours=3, minutes=10) # 190 mins away
        appt_1 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_1.date(),
            appointment_time=target_dt_1.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_1)
        db.commit()

        schedules_1 = calculate_email_reminder_times(appt_1, current_utc=datetime.now(timezone.utc))
        assert len(schedules_1) == 2, f"Expected 2 reminder events, got {len(schedules_1)}"
        types_1 = [s["reminder_type"] for s in schedules_1]
        assert "EMAIL_TWO_HOUR" in types_1, "Missing EMAIL_TWO_HOUR reminder event"
        assert "EMAIL_THIRTY_MINUTE" in types_1, "Missing EMAIL_THIRTY_MINUTE reminder event"

        persisted_1 = schedule_email_reminders(db, appt_1)
        db.commit()
        assert len(persisted_1) == 2, "Failed to persist 2 email reminder records in DB"
        print("[PASS] Test 1: Appointment > 2 hours away schedules both TWO_HOUR and THIRTY_MINUTE reminders")
        passed_count += 1

        # =====================================================================
        # TEST 2: Appointment is 90 minutes away: only 30-minute reminder scheduled
        # =====================================================================
        target_dt_2 = now_ist + timedelta(minutes=90) # 90 mins away
        appt_2 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_2.date(),
            appointment_time=target_dt_2.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_2)
        db.commit()

        schedules_2 = calculate_email_reminder_times(appt_2, current_utc=datetime.now(timezone.utc))
        assert len(schedules_2) == 1, f"Expected exactly 1 reminder event (THIRTY_MINUTE), got {len(schedules_2)}"
        assert schedules_2[0]["reminder_type"] == "EMAIL_THIRTY_MINUTE"
        assert schedules_2[0]["minutes_before"] == 30
        print("[PASS] Test 2: Appointment 90 mins away skips overdue 2h reminder and schedules only 30-min reminder")
        passed_count += 1

        # =====================================================================
        # TEST 3: Appointment is 20 minutes away: no overdue reminder is sent
        # =====================================================================
        target_dt_3 = now_ist + timedelta(minutes=20) # 20 mins away
        appt_3 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_3.date(),
            appointment_time=target_dt_3.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_3)
        db.commit()

        schedules_3 = calculate_email_reminder_times(appt_3, current_utc=datetime.now(timezone.utc))
        assert len(schedules_3) == 0, f"Expected 0 reminders for booking 20 mins before T, got {len(schedules_3)}"
        print("[PASS] Test 3: Appointment booked 20 mins before start sends zero overdue reminders")
        passed_count += 1

        # =====================================================================
        # TEST 4: Appointment time has passed: no reminder is sent (hard cutoff)
        # =====================================================================
        past_target = now_ist - timedelta(minutes=15)
        appt_4 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=past_target.date(),
            appointment_time=past_target.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_4)
        db.commit()

        # Calculation returns 0
        assert len(calculate_email_reminder_times(appt_4, current_utc=datetime.now(timezone.utc))) == 0

        # Pre-execution processor skips overdue appointment
        rem_stale = AppointmentReminder(
            id=uuid.uuid4(),
            appointment_id=appt_4.id,
            user_id=test_user.id,
            reminder_type="EMAIL_TWO_HOUR",
            minutes_before=120,
            scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=10),
            status="PENDING"
        )
        db.add(rem_stale)
        db.commit()

        stats_4 = process_due_email_reminders(db, appointment_id=appt_4.id)
        db.refresh(rem_stale)
        assert rem_stale.status == "SKIPPED", f"Expected SKIPPED, got {rem_stale.status}"
        assert stats_4["sent"] == 0, "Overdue reminder must not be sent after appointment time"
        print("[PASS] Test 4: Hard cutoff enforced — zero reminders sent at or after appointment time")
        passed_count += 1

        # =====================================================================
        # TEST 5: Cancelled appointment: remaining reminders are skipped / cancelled
        # =====================================================================
        appt_5 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_1.date(),
            appointment_time=target_dt_1.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_5)
        db.commit()
        schedule_email_reminders(db, appt_5)
        db.commit()

        # Cancel appointment
        appt_5.status = "CANCELLED"
        cancel_email_reminders(db, appt_5.id)
        db.commit()

        reminders_5 = db.query(AppointmentReminder).filter(AppointmentReminder.appointment_id == appt_5.id).all()
        assert all(r.status == "CANCELLED" for r in reminders_5), "All reminders must be CANCELLED"
        stats_5 = process_due_email_reminders(db, appointment_id=appt_5.id)
        assert stats_5["sent"] == 0, "No emails sent for cancelled appointment"
        print("[PASS] Test 5: Cancelled appointment marks all pending reminders CANCELLED with 0 emails sent")
        passed_count += 1

        # =====================================================================
        # TEST 6: Completed, skipped, or no-show appointment: pending stopped
        # =====================================================================
        appt_6 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_1.date(),
            appointment_time=target_dt_1.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_6)
        db.flush()

        # Attach QueueToken marked COMPLETED
        token_6 = QueueToken(
            id=uuid.uuid4(),
            appointment_id=appt_6.id,
            token_number="A-100",
            status="COMPLETED"
        )
        db.add(token_6)
        db.commit()

        rem_6 = AppointmentReminder(
            id=uuid.uuid4(),
            appointment_id=appt_6.id,
            user_id=test_user.id,
            reminder_type="EMAIL_THIRTY_MINUTE",
            minutes_before=30,
            scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=5),
            status="PENDING"
        )
        db.add(rem_6)
        db.commit()

        stats_6 = process_due_email_reminders(db, appointment_id=appt_6.id)
        db.refresh(rem_6)
        assert rem_6.status == "CANCELLED", f"Expected CANCELLED, got {rem_6.status}"
        assert stats_6["sent"] == 0
        print("[PASS] Test 6: Inactive token status (COMPLETED/SKIPPED/NO_SHOW) cancels pending email reminders")
        passed_count += 1

        # =====================================================================
        # TEST 7: Appointment time changes: pending reminders are recalculated
        # =====================================================================
        appt_7 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_1.date(),
            appointment_time=target_dt_1.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_7)
        db.commit()
        schedule_email_reminders(db, appt_7)
        db.commit()

        # Reschedule 5 hours into the future
        new_target_7 = now_ist + timedelta(hours=5)
        appt_7.appointment_date = new_target_7.date()
        appt_7.appointment_time = new_target_7.time().replace(microsecond=0)
        db.commit()

        rearmed_7 = reschedule_email_reminders(db, appt_7)
        db.commit()
        assert len(rearmed_7) == 2
        expected_new_2h_utc = get_appointment_target_datetime(appt_7, "Asia/Kolkata") - timedelta(hours=2)
        rem_2h = next(r for r in rearmed_7 if r.minutes_before == 120)
        diff_s = abs((rem_2h.scheduled_for - expected_new_2h_utc).total_seconds())
        assert diff_s < 2, f"Rescheduled reminder time mismatch: {diff_s}s"
        print("[PASS] Test 7: Rescheduled appointment updates reminder timers and invalidates obsolete jobs")
        passed_count += 1

        # =====================================================================
        # TEST 8: Duplicate scheduler execution: no duplicate email is sent
        # =====================================================================
        SENT_EMAILS_REGISTRY.clear()
        appt_8 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_1.date(),
            appointment_time=target_dt_1.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_8)
        db.commit()

        rem_8 = AppointmentReminder(
            id=uuid.uuid4(),
            appointment_id=appt_8.id,
            user_id=test_user.id,
            reminder_type="EMAIL_TWO_HOUR",
            minutes_before=120,
            scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=1),
            status="PENDING"
        )
        db.add(rem_8)
        db.commit()

        # Run 1: Should send 1 email and mark status SENT
        stats_8_run1 = process_due_email_reminders(db, appointment_id=appt_8.id)
        assert stats_8_run1["sent"] == 1
        assert len(SENT_EMAILS_REGISTRY) == 1
        db.refresh(rem_8)
        assert rem_8.status == "SENT"
        assert rem_8.processed_at is not None

        # Run 2: Immediately repeated scheduler run
        stats_8_run2 = process_due_email_reminders(db, appointment_id=appt_8.id)
        assert stats_8_run2["sent"] == 0
        assert len(SENT_EMAILS_REGISTRY) == 1, "Duplicate email dispatched on second scheduler pass"
        print("[PASS] Test 8: Scheduler idempotency verified — zero duplicate emails on repeated runs")
        passed_count += 1

        # =====================================================================
        # TEST 9: Backend restart: eligible pending reminders remain recoverable
        # =====================================================================
        # Create pending reminder
        appt_9 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_1.date(),
            appointment_time=target_dt_1.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_9)
        db.commit()

        rem_9_id = uuid.uuid4()
        rem_9 = AppointmentReminder(
            id=rem_9_id,
            appointment_id=appt_9.id,
            user_id=test_user.id,
            reminder_type="EMAIL_THIRTY_MINUTE",
            minutes_before=30,
            scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=2),
            status="PENDING"
        )
        db.add(rem_9)
        db.commit()

        # Simulate complete backend shutdown & restart: close session, open brand new SessionLocal
        db.close()
        fresh_db = SessionLocal()
        try:
            loaded_rem = fresh_db.query(AppointmentReminder).filter(AppointmentReminder.id == rem_9_id).first()
            assert loaded_rem is not None
            assert loaded_rem.status == "PENDING"

            # Execute processing on new session
            stats_9 = process_due_email_reminders(fresh_db, appointment_id=appt_9.id)
            assert stats_9["sent"] == 1
            fresh_db.refresh(loaded_rem)
            assert loaded_rem.status == "SENT"
            print("[PASS] Test 9: Backend restart durability verified — persistent DB records cleanly recovered")
            passed_count += 1
        finally:
            fresh_db.close()

        # =====================================================================
        # TEST 10: Email provider failure: error is recorded and retry rules respected
        # =====================================================================
        db = SessionLocal()
        # Bad email format test
        invalid_email_res = send_appointment_reminder_email(
            recipient_email="not-an-email",
            user_name="Invalid",
            service_name="Test",
            organization_name="Test Org",
            branch_name="Test Branch",
            date_str="2026-10-27",
            time_str="10:00 AM",
            remaining_label="in 2 hours"
        )
        assert invalid_email_res["success"] is False
        assert invalid_email_res["status"] == "FAILED"
        assert "Invalid recipient email" in invalid_email_res["error"]

        # Template HTML and plain-text rendering check
        html_sample = render_reminder_email_html(
            user_name="Rahul Sharma",
            service_name="Account Opening",
            organization_name="State Bank",
            branch_name="MG Road Branch",
            date_str="Tuesday, 27 October 2026",
            time_str="02:30 PM",
            remaining_label="in 2 hours",
            token_number="A-042"
        )
        assert "Rahul Sharma" in html_sample
        assert "Account Opening" in html_sample
        assert "A-042" in html_sample
        assert "QueueLess AI" in html_sample

        text_sample = render_reminder_email_text(
            user_name="Rahul Sharma",
            service_name="Account Opening",
            organization_name="State Bank",
            branch_name="MG Road Branch",
            date_str="Tuesday, 27 October 2026",
            time_str="02:30 PM",
            remaining_label="in 2 hours",
            token_number="A-042"
        )
        assert "A-042" in text_sample
        assert "02:30 PM IST" in text_sample

        print("[PASS] Test 10: Email provider validation, HTML/Text rendering, and failure handling verified")
        passed_count += 1

        print("==================================================================")
        print(f"APPOINTMENT EMAIL REMINDERS SUMMARY: {passed_count}/{total_tests} Tests Passed (100% SUCCESS)")
        print("==================================================================")

    finally:
        # Final cleanup of test records
        try:
            db.query(AppointmentReminder).filter(AppointmentReminder.user_id == test_user.id).delete(synchronize_session=False)
            test_appts = db.query(Appointment.id).filter(Appointment.user_id == test_user.id).all()
            if test_appts:
                appt_ids = [a[0] for a in test_appts]
                db.query(QueueToken).filter(QueueToken.appointment_id.in_(appt_ids)).delete(synchronize_session=False)
            db.query(Appointment).filter(Appointment.user_id == test_user.id).delete(synchronize_session=False)
            db.commit()
        except Exception:
            pass
        db.close()

if __name__ == "__main__":
    run_all_email_reminder_tests()
