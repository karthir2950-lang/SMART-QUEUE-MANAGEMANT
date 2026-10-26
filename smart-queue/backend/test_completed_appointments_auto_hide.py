import sys
import os
import uuid
from datetime import date, time as dt_time, datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db, SessionLocal
from app.models.domain import User, Appointment, Branch, Service, Sector, Organization, Staff, Counter, QueueToken, Notification
from app.core.security import get_current_user

client = TestClient(app)

def run_tests():
    db = SessionLocal()
    print("==================================================================")
    print("RUNNING QUEUELESS AI - COMPLETED APPOINTMENTS AUTO-HIDE TEST SUITE")
    print("==================================================================")
    passed_count = 0

    try:
        # 1. Setup Context from existing DB records
        admin_user = db.query(User).filter(User.role == 'ADMIN').first()
        staff_user = db.query(User).filter(User.role == 'STAFF').first()
        reg_user_a = db.query(User).filter(User.role == 'USER').first()
        reg_user_b = db.query(User).filter(User.role == 'USER', User.id != reg_user_a.id).first()

        if not reg_user_b:
            reg_user_b = User(
                id=uuid.uuid4(),
                name="Test User B",
                phone=f"999{uuid.uuid4().hex[:7]}",
                email=f"user_b_{uuid.uuid4().hex[:6]}@test.com",
                role="USER",
                status="ACTIVE"
            )
            db.add(reg_user_b)
            db.commit()
            db.refresh(reg_user_b)

        staff_record = db.query(Staff).filter(Staff.user_id == staff_user.id, Staff.status == 'ACTIVE').first()
        branch_id = staff_record.branch_id
        org_id = staff_record.organization_id

        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        org = db.query(Organization).filter(Organization.id == org_id).first()

        counter = db.query(Counter).filter(Counter.branch_id == branch_id).first()
        if not counter:
            counter = Counter(
                id=uuid.uuid4(),
                branch_id=branch_id,
                name="Counter #1",
                counter_number=1,
                status="AVAILABLE"
            )
            db.add(counter)
            db.commit()
            db.refresh(counter)

        service = db.query(Service).first()
        sector = db.query(Sector).filter(Sector.id == service.sector_id).first()
        today = date.today()

        # Clean prior test slot appointments
        db.query(Appointment).filter(
            Appointment.appointment_date == today,
            Appointment.user_id.in_([reg_user_a.id, reg_user_b.id]),
            Appointment.appointment_time.in_([dt_time(6, 15), dt_time(6, 30)])
        ).update({"status": "CANCELLED"}, synchronize_session=False)
        db.commit()

        # -------------------------------------------------------------
        # TEST 1: Active BOOKED appointment appears in My Appointments
        # -------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: reg_user_a

        appt_a = Appointment(
            id=uuid.uuid4(),
            user_id=reg_user_a.id,
            sector_id=sector.id,
            organization_id=org_id,
            branch_id=branch_id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=dt_time(6, 15),
            status="BOOKED"
        )
        db.add(appt_a)
        db.commit()
        db.refresh(appt_a)
        appt_a_id = str(appt_a.id)

        # Generate queue token
        res_tok = client.post(f"/api/queue/token/{appt_a_id}")
        assert res_tok.status_code == 200, f"Token gen failed: {res_tok.text}"
        token_id = res_tok.json()["id"]

        # Query GET /api/appointments/user
        res_user_appts = client.get("/api/appointments/user")
        assert res_user_appts.status_code == 200
        active_ids = [a["id"] for a in res_user_appts.json()]
        assert appt_a_id in active_ids, "Newly booked appointment must appear in active appointments"
        print("[PASS] Test 1: Active BOOKED appointment appears in GET /api/appointments/user")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 2: Staff completes appointment through authorized workflow
        # -------------------------------------------------------------
        # Transition token to CALLED at staff counter
        tok_obj = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(token_id)).first()
        tok_obj.status = 'CALLED'
        tok_obj.counter_id = counter.id
        tok_obj.called_at = datetime.now(timezone.utc)
        appt_a.status = 'CALLED'
        counter.current_token_id = tok_obj.id
        counter.status = 'BUSY'
        db.commit()

        # Switch to Staff user
        app.dependency_overrides[get_current_user] = lambda: staff_user

        # 1. Staff starts serving
        res_start = client.post(f"/api/staff/queue/{token_id}/start")
        assert res_start.status_code == 200, f"start failed: {res_start.text}"
        assert res_start.json()["status"] == "SERVING"

        # 2. Staff completes service
        res_comp = client.post(f"/api/staff/queue/{token_id}/complete")
        assert res_comp.status_code == 200, f"complete failed: {res_comp.text}"
        assert res_comp.json()["status"] == "COMPLETED"

        # Verify DB directly: Ensure appointment & token records are PRESERVED in PostgreSQL
        db.expire_all()
        db_appt = db.query(Appointment).filter(Appointment.id == uuid.UUID(appt_a_id)).first()
        assert db_appt is not None, "Appointment record must NEVER be deleted from database"
        assert db_appt.status == "COMPLETED", f"Appointment status should be COMPLETED, got {db_appt.status}"

        db_tok = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(token_id)).first()
        assert db_tok is not None, "Token record must NEVER be deleted from database"
        assert db_tok.status == "COMPLETED", f"Token status should be COMPLETED, got {db_tok.status}"
        print("[PASS] Test 2: Staff completes appointment -> DB records preserved with COMPLETED status")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 3: Completed appointment is automatically hidden from active appointments
        # -------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: reg_user_a

        # Calling GET /api/appointments/user without params must NOT return completed appointment
        res_after_comp = client.get("/api/appointments/user")
        assert res_after_comp.status_code == 200
        active_ids_after = [a["id"] for a in res_after_comp.json()]
        assert appt_a_id not in active_ids_after, "COMPLETED appointment must NOT appear in active list"

        # Calling GET /api/appointments/user?include_completed=true MUST return completed appointment
        res_with_completed = client.get("/api/appointments/user?include_completed=true")
        assert res_with_completed.status_code == 200
        all_ids = [a["id"] for a in res_with_completed.json()]
        assert appt_a_id in all_ids, "COMPLETED appointment must be available when include_completed=true for history"
        print("[PASS] Test 3: Completed appointment filtered from active list & preserved when include_completed=true")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 4: Notifications & History records preserved
        # -------------------------------------------------------------
        notif = db.query(Notification).filter(
            Notification.user_id == reg_user_a.id,
            Notification.appointment_id == uuid.UUID(appt_a_id),
            Notification.type == "COMPLETED"
        ).first()
        assert notif is not None, "Completion notification must exist for the user"
        print("[PASS] Test 4: Completion notification generated and verified in database")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 5: Cancelled appointments follow rules & cannot cancel COMPLETED
        # -------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: reg_user_a

        # Attempting to cancel a COMPLETED appointment must return 409 Conflict
        res_cancel_comp = client.post(f"/api/appointments/{appt_a_id}/cancel")
        assert res_cancel_comp.status_code == 409, f"Should reject cancelling COMPLETED appt, got {res_cancel_comp.status_code}"

        # Book a second appointment to test normal cancellation
        appt_2 = Appointment(
            id=uuid.uuid4(),
            user_id=reg_user_a.id,
            sector_id=sector.id,
            organization_id=org_id,
            branch_id=branch_id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=dt_time(6, 30),
            status="BOOKED"
        )
        db.add(appt_2)
        db.commit()
        db.refresh(appt_2)
        appt_2_id = str(appt_2.id)

        # Cancel appointment 2
        res_cancel = client.post(f"/api/appointments/{appt_2_id}/cancel")
        assert res_cancel.status_code == 200

        # Repeated cancel returns 409
        res_cancel_repeat = client.post(f"/api/appointments/{appt_2_id}/cancel")
        assert res_cancel_repeat.status_code == 409

        # Verify not in active appointments list
        res_check_cancel = client.get("/api/appointments/user")
        active_ids_cancel = [a["id"] for a in res_check_cancel.json()]
        assert appt_2_id not in active_ids_cancel, "Cancelled appointment must not be in active list"
        print("[PASS] Test 5: Cancellation rules strictly enforced & 409 conflict on completed/duplicate cancels")
        passed_count += 1

        # -------------------------------------------------------------
        # TEST 6: Cross-user authorization strictly enforced
        # -------------------------------------------------------------
        # Switch to User B
        app.dependency_overrides[get_current_user] = lambda: reg_user_b

        # User B should NOT be able to view User A's appointment details
        res_unauth_view = client.get(f"/api/appointments/{appt_a_id}")
        assert res_unauth_view.status_code == 403, f"Expected 403 for unauthorized view, got {res_unauth_view.status_code}"

        # User B should NOT be able to cancel User A's appointment
        res_unauth_cancel = client.post(f"/api/appointments/{appt_a_id}/cancel")
        assert res_unauth_cancel.status_code == 403, f"Expected 403 for unauthorized cancel, got {res_unauth_cancel.status_code}"

        # User B's active appointments must not contain User A's appointments
        res_b_appts = client.get("/api/appointments/user")
        assert res_b_appts.status_code == 200
        b_ids = [a["id"] for a in res_b_appts.json()]
        assert appt_a_id not in b_ids
        assert appt_2_id not in b_ids
        print("[PASS] Test 6: Cross-user authorization strictly enforced (403 on view/cancel)")
        passed_count += 1

        print("==================================================================")
        print(f"VERIFICATION SUMMARY: {passed_count} Passed, 0 Failed")
        print("ALL COMPLETED APPOINTMENTS AUTO-HIDE TESTS PASSED WITH 100% SUCCESS!")
        print("==================================================================")

    finally:
        app.dependency_overrides.clear()
        db.close()

if __name__ == "__main__":
    run_tests()
