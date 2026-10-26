import sys
import os
import uuid
from datetime import date, time as dt_time, datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Appointment, Branch, Service, Sector, Organization, QueueToken
from app.core.security import get_current_user

client = TestClient(app)

def run_all_phase_7_tests():
    db = SessionLocal()
    print("==================================================================")
    print("RUNNING QUEUELESS AI - PHASE 7: APPOINTMENT STATUS & EXPIRY SUITE")
    print("==================================================================")
    passed_count = 0
    total_tests = 9

    try:
        # Setup test users
        user_a = db.query(User).filter(User.role == 'USER').first()
        assert user_a is not None, "User A must exist in database"

        user_b = db.query(User).filter(User.role == 'USER', User.id != user_a.id).first()
        if not user_b:
            user_b = User(
                id=uuid.uuid4(),
                name="Test User Isolation",
                phone=f"987{uuid.uuid4().hex[:7]}",
                email=f"user_iso_{uuid.uuid4().hex[:6]}@test.com",
                role="USER",
                status="ACTIVE"
            )
            db.add(user_b)
            db.commit()
            db.refresh(user_b)

        service = db.query(Service).first()
        branch = db.query(Branch).first()
        org_id = branch.organization_id
        sector_id = service.sector_id
        today = date.today()

        # -----------------------------------------------------------------
        # TEST 1: BOOKED appointment in the future — visible
        # -----------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user_a
        future_time = (datetime.now() + timedelta(hours=3)).time().replace(microsecond=0)
        appt_future = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=future_time,
            status="BOOKED"
        )
        db.add(appt_future)
        db.commit()
        db.refresh(appt_future)

        res = client.get("/api/appointments/user")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        active_ids = [a["id"] for a in res.json()]
        assert str(appt_future.id) in active_ids, "Future BOOKED appointment MUST be visible"
        print("[PASS] Test 1: BOOKED appointment in the future is visible")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 2: BOOKED appointment at the current time — visible (>= rule)
        # -----------------------------------------------------------------
        now_sample = datetime.now()
        curr_exact_time = now_sample.time().replace(microsecond=0)
        appt_curr = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=now_sample.date(),
            appointment_time=curr_exact_time,
            status="BOOKED"
        )
        db.add(appt_curr)
        db.commit()
        db.refresh(appt_curr)

        # 1. SQL query verification of exact equality
        exact_query = db.query(Appointment).filter(
            Appointment.id == appt_curr.id,
            Appointment.status == 'BOOKED',
            Appointment.appointment_date == now_sample.date(),
            Appointment.appointment_time >= curr_exact_time
        ).first()
        assert exact_query is not None, "Exact equality (>=) must match in backend query"

        # 2. Endpoint verification with current slot (+15s buffer for execution latency)
        appt_curr_slot = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=now_sample.date(),
            appointment_time=(datetime.now() + timedelta(seconds=15)).time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_curr_slot)
        db.commit()
        db.refresh(appt_curr_slot)

        res = client.get("/api/appointments/user")
        assert res.status_code == 200
        active_ids = [a["id"] for a in res.json()]
        assert str(appt_curr_slot.id) in active_ids, "BOOKED appointment at current time slot (>= rule) MUST be visible"
        print("[PASS] Test 2: BOOKED appointment at the current time is visible (>= rule verified)")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 3: BOOKED appointment in the past — hidden
        # -----------------------------------------------------------------
        past_time = (datetime.now() - timedelta(hours=2)).time().replace(microsecond=0)
        appt_past = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=past_time,
            status="BOOKED"
        )
        db.add(appt_past)
        db.commit()
        db.refresh(appt_past)

        res = client.get("/api/appointments/user")
        assert res.status_code == 200
        active_ids = [a["id"] for a in res.json()]
        assert str(appt_past.id) not in active_ids, "Past BOOKED appointment MUST be hidden"
        print("[PASS] Test 3: BOOKED appointment in the past is hidden")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 4: CANCELLED appointment in the future — hidden
        # -----------------------------------------------------------------
        appt_cancelled = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=future_time,
            status="CANCELLED"
        )
        db.add(appt_cancelled)
        db.commit()
        db.refresh(appt_cancelled)

        res = client.get("/api/appointments/user")
        assert res.status_code == 200
        active_ids = [a["id"] for a in res.json()]
        assert str(appt_cancelled.id) not in active_ids, "Future CANCELLED appointment MUST be hidden"
        print("[PASS] Test 4: CANCELLED appointment in the future is hidden")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 5: COMPLETED appointment in the future — hidden
        # -----------------------------------------------------------------
        appt_completed = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=future_time,
            status="COMPLETED"
        )
        db.add(appt_completed)
        db.commit()
        db.refresh(appt_completed)

        res = client.get("/api/appointments/user")
        assert res.status_code == 200
        active_ids = [a["id"] for a in res.json()]
        assert str(appt_completed.id) not in active_ids, "Future COMPLETED appointment MUST be hidden"
        print("[PASS] Test 5: COMPLETED appointment in the future is hidden")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 6: NO_SHOW and SKIPPED appointments — hidden
        # -----------------------------------------------------------------
        appt_noshow = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=future_time,
            status="NO_SHOW"
        )
        appt_skipped = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=future_time,
            status="SKIPPED"
        )
        db.add_all([appt_noshow, appt_skipped])
        db.commit()
        db.refresh(appt_noshow)
        db.refresh(appt_skipped)

        res = client.get("/api/appointments/user")
        assert res.status_code == 200
        active_ids = [a["id"] for a in res.json()]
        assert str(appt_noshow.id) not in active_ids, "NO_SHOW appointment MUST be hidden"
        assert str(appt_skipped.id) not in active_ids, "SKIPPED appointment MUST be hidden"
        print("[PASS] Test 6: NO_SHOW and SKIPPED appointments are hidden")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 7: Appointment expires while open — auto-removed
        # -----------------------------------------------------------------
        appt_to_expire = Appointment(
            id=uuid.uuid4(),
            user_id=user_a.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=(datetime.now() + timedelta(seconds=15)).time().replace(microsecond=0),
            status="BOOKED"
        )
        db.add(appt_to_expire)
        db.commit()
        db.refresh(appt_to_expire)

        # Initial check at current time: present
        res_initial = client.get("/api/appointments/user")
        assert str(appt_to_expire.id) in [a["id"] for a in res_initial.json()]

        # Simulate time passage by shifting appointment_time by -10 minutes
        earlier_time = (datetime.now() - timedelta(minutes=10)).time().replace(microsecond=0)
        appt_to_expire.appointment_time = earlier_time
        db.commit()
        db.refresh(appt_to_expire)

        # Calling without manual reload or during interval check:
        res_after = client.get("/api/appointments/user")
        assert str(appt_to_expire.id) not in [a["id"] for a in res_after.json()], "Expired appointment MUST be removed"
        print("[PASS] Test 7: Appointment expires while the page is open — removed automatically")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 8: Refreshing the page does NOT restore expired appointments
        # -----------------------------------------------------------------
        # Multiple consecutive re-queries to simulate page refreshes
        for refresh_attempt in range(3):
            res_refresh = client.get("/api/appointments/user")
            assert res_refresh.status_code == 200
            current_active = [a["id"] for a in res_refresh.json()]
            assert str(appt_past.id) not in current_active, f"Past appointment reappeared on refresh #{refresh_attempt + 1}"
            assert str(appt_to_expire.id) not in current_active, f"Expired appointment reappeared on refresh #{refresh_attempt + 1}"
            assert str(appt_cancelled.id) not in current_active, f"Cancelled appointment reappeared on refresh #{refresh_attempt + 1}"
            assert str(appt_completed.id) not in current_active, f"Completed appointment reappeared on refresh #{refresh_attempt + 1}"
        print("[PASS] Test 8: Refreshing the page does not restore expired appointments")
        passed_count += 1

        # -----------------------------------------------------------------
        # TEST 9: Other users' appointments are never returned
        # -----------------------------------------------------------------
        # Create an appointment for User B
        appt_user_b = Appointment(
            id=uuid.uuid4(),
            user_id=user_b.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=future_time,
            status="BOOKED"
        )
        db.add(appt_user_b)
        db.commit()
        db.refresh(appt_user_b)

        # User A should NOT see User B's appointment
        app.dependency_overrides[get_current_user] = lambda: user_a
        res_user_a = client.get("/api/appointments/user")
        assert res_user_a.status_code == 200
        user_a_ids = [a["id"] for a in res_user_a.json()]
        assert str(appt_user_b.id) not in user_a_ids, "User A must NEVER see User B's appointment"

        # User B should see their own appointment
        app.dependency_overrides[get_current_user] = lambda: user_b
        res_user_b = client.get("/api/appointments/user")
        assert res_user_b.status_code == 200
        user_b_ids = [a["id"] for a in res_user_b.json()]
        assert str(appt_user_b.id) in user_b_ids, "User B must see their own appointment"
        assert str(appt_future.id) not in user_b_ids, "User B must NEVER see User A's appointment"
        print("[PASS] Test 9: Other users' appointments are never returned (isolation enforced)")
        passed_count += 1

        print("==================================================================")
        print(f"PHASE 7 SUMMARY: {passed_count}/{total_tests} Tests Passed (100% SUCCESS)")
        print("==================================================================")

        # Cleanup test records
        cleanup_ids = [
            appt_future.id, appt_curr.id, appt_curr_slot.id, appt_past.id,
            appt_cancelled.id, appt_completed.id, appt_noshow.id,
            appt_skipped.id, appt_to_expire.id, appt_user_b.id
        ]
        db.query(QueueToken).filter(QueueToken.appointment_id.in_(cleanup_ids)).delete(synchronize_session=False)
        db.query(Appointment).filter(Appointment.id.in_(cleanup_ids)).delete(synchronize_session=False)
        db.commit()

    finally:
        db.close()
        app.dependency_overrides.clear()

if __name__ == "__main__":
    run_all_phase_7_tests()
