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
from app.models.domain import User, Appointment, Branch, Service, Sector, Organization, QueueToken, AppointmentReminder, Notification
from app.core.security import get_current_user
from app.services.reminder_service import (
    get_appointment_target_datetime,
    calculate_future_reminder_times,
    schedule_appointment_reminders,
    cancel_appointment_reminders,
    reschedule_appointment_reminders,
    process_due_reminders,
    resolve_timezone
)

client = TestClient(app)

def run_all_appointment_reminder_tests():
    db = SessionLocal()
    print("==================================================================")
    print("RUNNING QUEUELESS AI: SMART APPOINTMENT REMINDERS TEST SUITE")
    print("==================================================================")
    passed_count = 0
    total_tests = 11

    # Setup shared test context
    test_user_a = db.query(User).filter(User.email == "user_a_reminder_test@example.com").first()
    if not test_user_a:
        test_user_a = User(
            id=uuid.uuid4(),
            name="Reminder Test User A",
            email="user_a_reminder_test@example.com",
            phone="+919876543201",
            role="USER",
            status="ACTIVE"
        )
        db.add(test_user_a)

    test_user_b = db.query(User).filter(User.email == "user_b_reminder_test@example.com").first()
    if not test_user_b:
        test_user_b = User(
            id=uuid.uuid4(),
            name="Reminder Test User B",
            email="user_b_reminder_test@example.com",
            phone="+919876543202",
            role="USER",
            status="ACTIVE"
        )
        db.add(test_user_b)

    branch = db.query(Branch).first()
    service = db.query(Service).first()
    db.commit()

    # Clean up any leftover test data for isolated test runs
    test_uids = [test_user_a.id, test_user_b.id]
    db.query(AppointmentReminder).filter(AppointmentReminder.user_id.in_(test_uids)).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.user_id.in_(test_uids)).delete(synchronize_session=False)
    test_appts = db.query(Appointment.id).filter(Appointment.user_id.in_(test_uids)).all()
    if test_appts:
        appt_ids = [a[0] for a in test_appts]
        db.query(QueueToken).filter(QueueToken.appointment_id.in_(appt_ids)).delete(synchronize_session=False)
    db.query(Appointment).filter(Appointment.user_id.in_(test_uids)).delete(synchronize_session=False)
    db.commit()

    IST = resolve_timezone("Asia/Kolkata")

    try:
        # =================================================================
        # TEST 1: Appointment > 2 hours away schedules first reminder at T-120
        # =================================================================
        now_ist = datetime.now(IST)
        target_dt_1 = now_ist + timedelta(hours=3) # 180 mins away
        appt_1 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
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
        appt_1_id = appt_1.id

        reminders_1 = schedule_appointment_reminders(db, appt_1, current_utc=datetime.now(timezone.utc))
        db.commit()

        # Must have scheduled T-120
        t120 = next((r for r in reminders_1 if r.reminder_type == "T_MINUS_120"), None)
        assert t120 is not None, "T_MINUS_120 reminder must be scheduled for appointment > 2h away"
        expected_t120_utc = target_dt_1.astimezone(timezone.utc) - timedelta(minutes=120)
        diff_seconds = abs((t120.scheduled_for - expected_t120_utc).total_seconds())
        assert diff_seconds < 2, f"T_MINUS_120 scheduled time diff too large: {diff_seconds}s"
        print("[PASS] Test 1: Appointment > 2 hours away correctly schedules first reminder at T-120 minutes")
        passed_count += 1

        # =================================================================
        # TEST 2: Verify subsequent reminders at T-90, T-60, and T-30 minutes
        # =================================================================
        r_types = {r.reminder_type for r in reminders_1}
        assert r_types == {"T_MINUS_120", "T_MINUS_90", "T_MINUS_60", "T_MINUS_30"}, (
            f"Expected all 4 reminder types, got {r_types}"
        )

        # Simulate time moving to T-120 and processing
        t_120_due = target_dt_1.astimezone(timezone.utc) - timedelta(minutes=120) + timedelta(seconds=1)
        res_due_1 = process_due_reminders(db, reference_now_utc=t_120_due)
        assert res_due_1["processed"] == 1, f"Expected 1 reminder processed at T-120, got {res_due_1['processed']}"

        # Verify notification created
        notif_t120 = db.query(Notification).filter(
            Notification.user_id == test_user_a.id,
            Notification.appointment_id == appt_1.id,
            Notification.type == "APPOINTMENT_REMINDER"
        ).first()
        assert notif_t120 is not None, "Notification must be created for T-120 reminder"
        assert "2 hours" in notif_t120.title or "2 hours" in notif_t120.message

        # Simulate subsequent reminders T-90, T-60, T-30
        t_90_due = target_dt_1.astimezone(timezone.utc) - timedelta(minutes=90) + timedelta(seconds=1)
        res_due_90 = process_due_reminders(db, reference_now_utc=t_90_due)
        assert res_due_90["processed"] == 1, "T-90 reminder must be processed"

        t_60_due = target_dt_1.astimezone(timezone.utc) - timedelta(minutes=60) + timedelta(seconds=1)
        res_due_60 = process_due_reminders(db, reference_now_utc=t_60_due)
        assert res_due_60["processed"] == 1, "T-60 reminder must be processed"

        t_30_due = target_dt_1.astimezone(timezone.utc) - timedelta(minutes=30) + timedelta(seconds=1)
        res_due_30 = process_due_reminders(db, reference_now_utc=t_30_due)
        assert res_due_30["processed"] == 1, "T-30 reminder must be processed"

        print("[PASS] Test 2: Subsequent reminders at T-90, T-60, and T-30 minutes processed accurately with descriptive messages")
        passed_count += 1

        # =================================================================
        # TEST 3: Verify no reminder is sent at or after T
        # =================================================================
        target_dt_3 = now_ist + timedelta(hours=3)
        appt_3 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
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
        schedule_appointment_reminders(db, appt_3, current_utc=datetime.now(timezone.utc))
        db.commit()

        # Simulate clock jumping straight to appointment time T (and after T) without previous runs
        at_or_after_t = target_dt_3.astimezone(timezone.utc) + timedelta(minutes=5)
        res_after_t = process_due_reminders(db, reference_now_utc=at_or_after_t)
        # Any unprocessed reminder whose scheduled time was before T must be marked SKIPPED, NOT processed!
        assert res_after_t["processed"] == 0, f"Expected 0 reminders processed after T, got {res_after_t['processed']}"
        assert res_after_t["skipped"] >= 1, "Pending reminders must be SKIPPED once appointment time has arrived"

        notif_after_t = db.query(Notification).filter(
            Notification.user_id == test_user_a.id,
            Notification.appointment_id == appt_3.id,
            Notification.type == "APPOINTMENT_REMINDER"
        ).count()
        assert notif_after_t == 0, "No notifications may ever be sent at or after appointment time T"
        print("[PASS] Test 3: Zero reminders sent at or after appointment time T (strict cutoff enforced)")
        passed_count += 1

        # =================================================================
        # TEST 4: Appointment booked less than 2 hours before T (no overdue reminders)
        # =================================================================
        # Subcase 4A: Booked 75 minutes before T -> only T-60 and T-30 are valid
        target_dt_4a = now_ist + timedelta(minutes=75)
        appt_4a = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_4a.date(),
            appointment_time=target_dt_4a.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_4a)
        db.commit()
        rem_4a = schedule_appointment_reminders(db, appt_4a, current_utc=datetime.now(timezone.utc))
        types_4a = {r.reminder_type for r in rem_4a}
        assert "T_MINUS_120" not in types_4a, "Overdue T_MINUS_120 reminder must NOT be scheduled"
        assert "T_MINUS_90" not in types_4a, "Overdue T_MINUS_90 reminder must NOT be scheduled"
        assert types_4a == {"T_MINUS_60", "T_MINUS_30"}, f"Expected only future reminders, got {types_4a}"

        # Subcase 4B: Booked 15 minutes before T -> 0 reminders scheduled
        target_dt_4b = now_ist + timedelta(minutes=15)
        appt_4b = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_4b.date(),
            appointment_time=target_dt_4b.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_4b)
        db.commit()
        rem_4b = schedule_appointment_reminders(db, appt_4b, current_utc=datetime.now(timezone.utc))
        assert len(rem_4b) == 0, f"Expected 0 reminders for 15-minute booking, got {len(rem_4b)}"
        print("[PASS] Test 4: Booking created < 2 hours before T schedules only valid future reminders (no overdue spam)")
        passed_count += 1

        # =================================================================
        # TEST 5: Cancelled appointment: no future reminders
        # =================================================================
        target_dt_5 = now_ist + timedelta(hours=4)
        appt_5 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_5.date(),
            appointment_time=target_dt_5.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_5)
        db.commit()
        schedule_appointment_reminders(db, appt_5, current_utc=datetime.now(timezone.utc))
        db.commit()

        # Authenticated cancellation via endpoint
        app.dependency_overrides[get_current_user] = lambda: test_user_a
        cancel_resp = client.post(f"/api/appointments/{appt_5.id}/cancel")
        assert cancel_resp.status_code == 200, f"Cancellation failed: {cancel_resp.text}"

        # Verify reminders cancelled in database
        pending_5 = db.query(AppointmentReminder).filter(
            AppointmentReminder.appointment_id == appt_5.id,
            AppointmentReminder.status == "PENDING"
        ).count()
        assert pending_5 == 0, f"All pending reminders must be cancelled, found {pending_5}"

        # Process due reminders at T-120: zero notifications sent
        t_120_5 = target_dt_5.astimezone(timezone.utc) - timedelta(minutes=120) + timedelta(seconds=1)
        res_cancel = process_due_reminders(db, reference_now_utc=t_120_5)
        notif_cancel = db.query(Notification).filter(
            Notification.user_id == test_user_a.id,
            Notification.appointment_id == appt_5.id,
            Notification.type == "APPOINTMENT_REMINDER"
        ).count()
        assert notif_cancel == 0, "No reminder notifications can be sent for a cancelled appointment"
        print("[PASS] Test 5: Cancelled appointment invalidates all pending reminders immediately")
        passed_count += 1

        # =================================================================
        # TEST 6: Completed, skipped, or no-show appointment: no future reminders
        # =================================================================
        for test_status in ["COMPLETED", "SKIPPED", "NO_SHOW"]:
            target_dt_6 = now_ist + timedelta(hours=4)
            appt_6 = Appointment(
                id=uuid.uuid4(),
                user_id=test_user_a.id,
                sector_id=service.sector_id if service else branch.organization.sector_id,
                organization_id=branch.organization_id,
                branch_id=branch.id,
                service_id=service.id,
                appointment_date=target_dt_6.date(),
                appointment_time=target_dt_6.time().replace(microsecond=0),
                status=test_status
            )
            db.add(appt_6)
            db.commit()
            cancel_appointment_reminders(db, appt_6.id)

            t_120_6 = target_dt_6.astimezone(timezone.utc) - timedelta(minutes=120) + timedelta(seconds=1)
            res_term = process_due_reminders(db, reference_now_utc=t_120_6)
            notif_term = db.query(Notification).filter(
                Notification.user_id == test_user_a.id,
                Notification.appointment_id == appt_6.id,
                Notification.type == "APPOINTMENT_REMINDER"
            ).count()
            assert notif_term == 0, f"No reminders allowed for status {test_status}"

        print("[PASS] Test 6: Inactive appointment statuses (COMPLETED, SKIPPED, NO_SHOW) disallow reminders")
        passed_count += 1

        # =================================================================
        # TEST 7: Rescheduled appointment: only the new valid schedule remains
        # =================================================================
        target_dt_7a = now_ist + timedelta(hours=3)
        appt_7 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_7a.date(),
            appointment_time=target_dt_7a.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_7)
        db.commit()
        schedule_appointment_reminders(db, appt_7, current_utc=datetime.now(timezone.utc))
        db.commit()

        # Reschedule appointment to +6 hours
        target_dt_7b = now_ist + timedelta(hours=6)
        resched_payload = {
            "appointment_date": str(target_dt_7b.date()),
            "appointment_time": str(target_dt_7b.time().replace(microsecond=0)),
            "notes": "Rescheduled for testing"
        }
        resched_res = client.post(f"/api/appointments/{appt_7.id}/reschedule", json=resched_payload)
        assert resched_res.status_code == 200, f"Reschedule failed: {resched_res.text}"

        # Verify reminders recalculated
        active_rem_7 = db.query(AppointmentReminder).filter(
            AppointmentReminder.appointment_id == appt_7.id,
            AppointmentReminder.status == "PENDING"
        ).all()
        assert len(active_rem_7) == 4, f"Expected 4 active reminders after reschedule, found {len(active_rem_7)}"
        new_t120 = next(r for r in active_rem_7 if r.reminder_type == "T_MINUS_120")
        expected_new_t120 = target_dt_7b.astimezone(timezone.utc) - timedelta(minutes=120)
        diff_resched = abs((new_t120.scheduled_for - expected_new_t120).total_seconds())
        assert diff_resched < 2, f"Rescheduled reminder timestamp mismatch: {diff_resched}s"
        print("[PASS] Test 7: Rescheduling appointment updates schedule and invalidates obsolete timers")
        passed_count += 1

        # =================================================================
        # TEST 8: Repeated scheduler runs produce NO duplicate notifications (Idempotency)
        # =================================================================
        target_dt_8 = now_ist + timedelta(hours=3)
        appt_8 = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=target_dt_8.date(),
            appointment_time=target_dt_8.time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_8)
        db.commit()
        appt_8_id = appt_8.id
        schedule_appointment_reminders(db, appt_8, current_utc=datetime.now(timezone.utc))
        db.commit()

        # Run 1: Due time T-120
        t_due_8 = target_dt_8.astimezone(timezone.utc) - timedelta(minutes=120) + timedelta(seconds=1)
        res_r1 = process_due_reminders(db, reference_now_utc=t_due_8)
        assert res_r1["processed"] == 1, "First run must process the reminder"

        # Run 2: Exact same time
        res_r2 = process_due_reminders(db, reference_now_utc=t_due_8)
        assert res_r2["processed"] == 0, "Second run must not re-process the reminder"

        # Run 3: A minute later
        res_r3 = process_due_reminders(db, reference_now_utc=t_due_8 + timedelta(minutes=1))
        assert res_r3["processed"] == 0, "Third run must not re-process the reminder"

        # Check total notifications created for this reminder interval
        total_notifs_8 = db.query(Notification).filter(
            Notification.user_id == test_user_a.id,
            Notification.appointment_id == appt_8_id,
            Notification.type == "APPOINTMENT_REMINDER",
            Notification.title.ilike("%2 hours%")
        ).count()
        assert total_notifs_8 == 1, f"Expected exactly 1 notification, got {total_notifs_8}"
        print("[PASS] Test 8: Repeated scheduler runs are strictly idempotent (zero duplicates)")
        passed_count += 1

        # =================================================================
        # TEST 9: Backend restart: pending reminders remain recoverable in database
        # =================================================================
        # Close current session completely
        db.close()

        # Reopen brand new database session simulating post-restart state
        fresh_db = SessionLocal()
        persisted_rem = fresh_db.query(AppointmentReminder).filter(
            AppointmentReminder.appointment_id == appt_8_id
        ).all()
        assert len(persisted_rem) == 4, "All 4 reminder records must persist in database across process lifecycles"
        processed_persisted = [r for r in persisted_rem if r.status == "PROCESSED"]
        pending_persisted = [r for r in persisted_rem if r.status == "PENDING"]
        assert len(processed_persisted) == 1, "Status PROCESSED must survive restart"
        assert len(pending_persisted) == 3, "Status PENDING must survive restart"
        fresh_db.close()
        db = SessionLocal() # reopen for rest of tests
        print("[PASS] Test 9: Backend restart preserves durable database reminder schedules")
        passed_count += 1

        # =================================================================
        # TEST 10: Authorization: User A cannot read User B's reminders or notifications
        # =================================================================
        # User B queries User A's appointment reminders -> HTTP 403 Forbidden
        app.dependency_overrides[get_current_user] = lambda: test_user_b
        leak_check = client.get(f"/api/appointments/{appt_1_id}/reminders")
        assert leak_check.status_code == 403, f"Expected 403 Forbidden for cross-user reminder read, got {leak_check.status_code}"

        # User B queries notifications -> User A's notifications must NOT appear
        notifs_b_resp = client.get("/api/notifications")
        assert notifs_b_resp.status_code == 200
        b_notifs = notifs_b_resp.json()["notifications"]
        assert all(n["user_id"] == str(test_user_b.id) for n in b_notifs), "User B received another user's notifications"
        print("[PASS] Test 10: Cross-user authorization strictly enforced (HTTP 403 and tenant isolation)")
        passed_count += 1

        # =================================================================
        # TEST 11: Timezone and midnight date-boundary calculations
        # =================================================================
        # Appointment at 01:00 AM on next day in Asia/Kolkata
        tomorrow_date = (datetime.now(IST) + timedelta(days=2)).date()
        midnight_time = dt_time(1, 0, 0) # 01:00 AM IST
        appt_boundary = Appointment(
            id=uuid.uuid4(),
            user_id=test_user_a.id,
            sector_id=service.sector_id if service else branch.organization.sector_id,
            organization_id=branch.organization_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=tomorrow_date,
            appointment_time=midnight_time,
            status="BOOKED"
        )
        db.add(appt_boundary)
        db.commit()

        # T-120 minutes is 11:00 PM (23:00) on PREVIOUS day!
        appt_utc = get_appointment_target_datetime(appt_boundary, "Asia/Kolkata")
        schedules_boundary = calculate_future_reminder_times(appt_boundary, current_utc=datetime.now(timezone.utc), tz_name="Asia/Kolkata")
        t120_sched = next(s for s in schedules_boundary if s["reminder_type"] == "T_MINUS_120")
        
        # Verify 120 minutes prior in local IST is 23:00 on day before
        t120_local = t120_sched["scheduled_for"].astimezone(IST)
        assert t120_local.time().hour == 23, f"Expected hour 23 on date boundary, got {t120_local.time().hour}"
        assert t120_local.time().minute == 0
        assert t120_local.date() == (tomorrow_date - timedelta(days=1))
        print("[PASS] Test 11: Date-boundary crossing (midnight/prior-day) and Asia/Kolkata timezone computed accurately")
        passed_count += 1

        # Reset overrides
        app.dependency_overrides.clear()

        print("==================================================================")
        print(f"APPOINTMENT REMINDERS SUMMARY: {passed_count}/{total_tests} Tests Passed (100% SUCCESS)")
        print("==================================================================")

    finally:
        app.dependency_overrides.clear()
        db.close()

if __name__ == "__main__":
    run_all_appointment_reminder_tests()
