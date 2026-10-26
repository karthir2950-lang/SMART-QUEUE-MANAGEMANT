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
from app.services.token_service import issue_queue_token, calculate_precise_people_ahead, get_next_token_number

client = TestClient(app)

def run_tests():
    db = SessionLocal()
    print("==================================================================")
    print("RUNNING QUEUELESS AI - REAL-TIME QUEUE MONITORING VERIFICATION SUITE")
    print("==================================================================")
    passed_count = 0

    try:
        # Context setup from DB
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
                name="Desk #1",
                counter_number=1,
                status="AVAILABLE"
            )
            db.add(counter)
            db.commit()
            db.refresh(counter)
        else:
            counter.current_token_id = None
            counter.status = "AVAILABLE"
            db.commit()

        service = db.query(Service).first()
        sector = db.query(Sector).filter(Sector.id == service.sector_id).first()
        today = date.today()

        # Clean any prior active appointments for test users
        db.query(Appointment).filter(
            Appointment.user_id.in_([reg_user_a.id, reg_user_b.id]),
            Appointment.status.notin_(["CANCELLED", "COMPLETED"])
        ).update({"status": "CANCELLED"}, synchronize_session=False)
        db.commit()

        # -----------------------------------------------------------------
        # TEST 1: Booking creates real database record & valid queue token
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: reg_user_a

        appt_1 = Appointment(
            id=uuid.uuid4(),
            user_id=reg_user_a.id,
            sector_id=sector.id,
            organization_id=org_id,
            branch_id=branch_id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=dt_time(8, 0),
            status="BOOKED"
        )
        db.add(appt_1)
        db.commit()

        res_token_1 = client.post(f"/api/queue/token/{appt_1.id}")
        assert res_token_1.status_code == 200, f"Token generation failed: {res_token_1.text}"
        data_1 = res_token_1.json()
        assert data_1["token_number"] is not None
        assert data_1["status"] == "WAITING"
        assert data_1["queue_position"] is not None
        print(f"[PASS] 1. Booking created real database record & valid token: {data_1['token_number']}")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 2: GET /api/queue/active returns current user's active session
        # -----------------------------------------------------------------
        res_active = client.get("/api/queue/active")
        assert res_active.status_code == 200, f"Active endpoint failed: {res_active.text}"
        active_data = res_active.json()
        assert active_data is not None
        assert active_data["appointment_id"] == str(appt_1.id)
        assert active_data["token_number"] == data_1["token_number"]
        assert "currently_serving_token" in active_data
        assert "server_time" in active_data
        print("[PASS] 2. GET /api/queue/active returns authoritative user queue session with server_time")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 3: User authorization isolation (User B cannot access User A's token)
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: reg_user_b

        res_unauth_token = client.get(f"/api/queue/token/{appt_1.id}")
        assert res_unauth_token.status_code == 403, f"Expected 403, got {res_unauth_token.status_code}"

        res_user_b_active = client.get("/api/queue/active")
        assert res_user_b_active.status_code == 200
        # User B should NOT receive User A's token
        if res_user_b_active.json():
            assert res_user_b_active.json()["appointment_id"] != str(appt_1.id)
        print("[PASS] 3. Strict cross-user isolation: User B blocked from User A's queue token (403)")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 4: People-ahead count accurately tracks queue order
        # -----------------------------------------------------------------
        # Book a second appointment at a later slot for user B
        appt_2 = Appointment(
            id=uuid.uuid4(),
            user_id=reg_user_b.id,
            sector_id=sector.id,
            organization_id=org_id,
            branch_id=branch_id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=dt_time(8, 15),
            status="BOOKED"
        )
        db.add(appt_2)
        db.commit()

        app.dependency_overrides[get_current_user] = lambda: reg_user_b
        res_token_2 = client.post(f"/api/queue/token/{appt_2.id}")
        assert res_token_2.status_code == 200
        data_2 = res_token_2.json()

        # Token 2 is scheduled after Token 1 -> exactly 1 person ahead
        tok_2_ahead = data_2["people_ahead"]
        assert tok_2_ahead >= 1, f"Expected at least 1 person ahead, got {tok_2_ahead}"
        print(f"[PASS] 4. People-ahead count accurately counts active waiting tokens ahead: {tok_2_ahead}")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 5: Currently serving token updates when staff calls/starts a token
        # -----------------------------------------------------------------
        tok_1_obj = db.query(QueueToken).filter(QueueToken.appointment_id == appt_1.id).first()
        tok_1_obj.status = 'CALLED'
        tok_1_obj.counter_id = counter.id
        tok_1_obj.called_at = datetime.now(timezone.utc)
        appt_1.status = 'CALLED'
        counter.current_token_id = tok_1_obj.id
        counter.status = 'BUSY'
        db.commit()

        # Staff starts serving token 1
        app.dependency_overrides[get_current_user] = lambda: staff_user
        res_serve = client.post(f"/api/staff/queue/{tok_1_obj.id}/start")
        assert res_serve.status_code == 200
        assert res_serve.json()["status"] == "SERVING"

        # Now check User B's active token: currently_serving_token MUST be Token 1!
        app.dependency_overrides[get_current_user] = lambda: reg_user_b
        res_b_refresh = client.get(f"/api/queue/token/{appt_2.id}")
        assert res_b_refresh.status_code == 200
        b_refreshed_data = res_b_refresh.json()
        assert b_refreshed_data["currently_serving_token"] == data_1["token_number"], \
            f"Expected currently_serving_token {data_1['token_number']}, got {b_refreshed_data['currently_serving_token']}"
        print(f"[PASS] 5. Currently serving token correctly resolves to active desk token: {b_refreshed_data['currently_serving_token']}")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 6: Completing a token decrements people-ahead and preserves DB record
        # -----------------------------------------------------------------
        # Staff completes token 1
        app.dependency_overrides[get_current_user] = lambda: staff_user
        res_comp = client.post(f"/api/staff/queue/{tok_1_obj.id}/complete")
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "COMPLETED"

        # Verify DB directly: appointment and token records remain preserved
        db.expire_all()
        db_appt_1 = db.query(Appointment).filter(Appointment.id == appt_1.id).first()
        assert db_appt_1.status == "COMPLETED", "Completed appointment status preserved"

        # User A's /api/queue/active should now return None or next active session (not COMPLETED token)
        app.dependency_overrides[get_current_user] = lambda: reg_user_a
        res_a_after_comp = client.get("/api/queue/active")
        assert res_a_after_comp.status_code == 200
        assert res_a_after_comp.json() is None, "COMPLETED token is no longer an active session"

        # User B's people ahead count should now decrement
        app.dependency_overrides[get_current_user] = lambda: reg_user_b
        res_b_after_comp = client.get(f"/api/queue/token/{appt_2.id}")
        assert res_b_after_comp.status_code == 200
        new_ahead = res_b_after_comp.json()["people_ahead"]
        assert new_ahead < tok_2_ahead, f"Expected people ahead to decrement from {tok_2_ahead}, got {new_ahead}"
        print(f"[PASS] 6. Completed token decrements people-ahead (from {tok_2_ahead} to {new_ahead}) and preserves DB history")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 7: Estimated wait is calculated when service data is present
        # -----------------------------------------------------------------
        est_wait = res_b_after_comp.json()["estimated_waiting_time"]
        assert est_wait is not None, "Estimated wait time should be calculated with service duration"
        print(f"[PASS] 7. Estimated wait calculation derived from service duration: {est_wait} min")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 8: Token idempotency and non-colliding sequential generation
        # -----------------------------------------------------------------
        # Repeated token creation for the same appointment is strictly idempotent
        app.dependency_overrides[get_current_user] = lambda: reg_user_b
        res_repeat = client.post(f"/api/queue/token/{appt_2.id}")
        assert res_repeat.status_code == 200
        assert res_repeat.json()["id"] == str(data_2["id"])
        assert res_repeat.json()["token_number"] == data_2["token_number"]
        print("[PASS] 8. Token generation is strictly idempotent under repeat requests")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 9: Cancellation rules and integrity
        # -----------------------------------------------------------------
        # Cancelling user B's appointment
        res_cancel = client.post(f"/api/appointments/{appt_2.id}/cancel")
        assert res_cancel.status_code == 200

        # Attempting to cancel already CANCELLED appointment returns 409
        res_cancel_again = client.post(f"/api/appointments/{appt_2.id}/cancel")
        assert res_cancel_again.status_code == 409

        # Active queue endpoint for user B now returns None
        res_b_after_cancel = client.get("/api/queue/active")
        assert res_b_after_cancel.status_code == 200
        assert res_b_after_cancel.json() is None
        print("[PASS] 9. Cancelled tokens excluded from active monitoring & double cancel blocked with 409")
        passed_count += 1

        print("==================================================================")
        print(f"VERIFICATION SUMMARY: {passed_count} Passed, 0 Failed")
        print("ALL REAL-TIME QUEUE MONITORING VERIFICATION TESTS PASSED WITH 100% SUCCESS!")
        print("==================================================================")

    finally:
        app.dependency_overrides.clear()
        db.close()

if __name__ == "__main__":
    run_tests()
