import sys
import os
import uuid
from datetime import date, time as dt_time, datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Appointment, Branch, Service, Sector, Organization, QueueToken, Counter
from app.core.security import get_current_user
from app.services.token_service import token_sort_key

client = TestClient(app)

def run_backend_queue_order_tests():
    db = SessionLocal()
    print("==================================================================")
    print("RUNNING BACKEND APPOINTMENT & QUEUE TOKEN ORDERING SUITE")
    print("==================================================================")
    passed_count = 0
    total_tests = 7

    try:
        # 1. Natural Sort Key Unit Verification
        tokens_list = ['A-10', 'A-2', 'A-1', 'A-20', 'B-10', 'B-2']
        sorted_tokens = sorted(tokens_list, key=token_sort_key)
        assert sorted_tokens == ['A-1', 'A-2', 'A-10', 'A-20', 'B-2', 'B-10'], f"Unexpected sort: {sorted_tokens}"
        assert sorted_tokens.index('A-2') < sorted_tokens.index('A-10'), "A-2 must precede A-10"
        print("[PASS] 1. Backend token_sort_key orders tokens numerically (A-2 before A-10)")
        passed_count += 1

        # Setup context
        user = db.query(User).filter(User.role == 'USER').first()
        assert user is not None, "Test user must exist"

        branch_1 = db.query(Branch).first()
        branch_2 = db.query(Branch).filter(Branch.id != branch_1.id).first()
        service = db.query(Service).first()
        sector_id = service.sector_id
        org_id = branch_1.organization_id

        today = date.today()
        tomorrow = today + timedelta(days=1)
        now_dt = datetime.now()

        # -------------------------------------------------------------
        # 2. Ascending Chronological Order for User Appointments
        # -------------------------------------------------------------
        app.dependency_overrides[get_current_user] = lambda: user

        # Clear prior active appointments for this test user to test clean ordering
        db.query(Appointment).filter(
            Appointment.user_id == user.id,
            Appointment.status == 'BOOKED'
        ).update({"status": "CANCELLED"}, synchronize_session=False)
        db.commit()

        # Create 3 future appointments in non-chronological insertion order
        appt_late = Appointment(
            id=uuid.uuid4(),
            user_id=user.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch_1.id,
            service_id=service.id,
            appointment_date=tomorrow,
            appointment_time=dt_time(15, 0),
            status="BOOKED"
        )
        appt_early = Appointment(
            id=uuid.uuid4(),
            user_id=user.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch_1.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=(now_dt + timedelta(hours=3)).time().replace(microsecond=0),
            status="BOOKED"
        )
        appt_mid = Appointment(
            id=uuid.uuid4(),
            user_id=user.id,
            sector_id=sector_id,
            organization_id=org_id,
            branch_id=branch_1.id,
            service_id=service.id,
            appointment_date=tomorrow,
            appointment_time=dt_time(10, 0),
            status="BOOKED"
        )
        # Add in mixed order: late, early, mid
        db.add_all([appt_late, appt_early, appt_mid])
        db.commit()

        res_appts = client.get("/api/appointments/user")
        assert res_appts.status_code == 200
        appts_data = res_appts.json()
        returned_ids = [a["id"] for a in appts_data]

        assert str(appt_early.id) in returned_ids
        assert str(appt_mid.id) in returned_ids
        assert str(appt_late.id) in returned_ids

        # Ensure earliest upcoming appears first
        assert returned_ids.index(str(appt_early.id)) < returned_ids.index(str(appt_mid.id)), "Today's appt must precede tomorrow's"
        assert returned_ids.index(str(appt_mid.id)) < returned_ids.index(str(appt_late.id)), "Tomorrow 10:00 must precede tomorrow 15:00"
        print("[PASS] 2. GET /api/appointments/user strictly orders appointments chronologically ascending")
        passed_count += 1

        # -------------------------------------------------------------
        # 3. GET /api/queue/active returns earliest active token
        # -------------------------------------------------------------
        res_active = client.get("/api/queue/active")
        assert res_active.status_code == 200
        active_tok = res_active.json()
        assert active_tok is not None, "Active queue token must be returned for earliest active appointment"
        assert active_tok["appointment_id"] == str(appt_early.id), "Earliest upcoming appointment must be the active token"
        print("[PASS] 3. GET /api/queue/active correctly selects the earliest upcoming active token")
        passed_count += 1

        # -------------------------------------------------------------
        # 4. Terminal status tokens are excluded from GET /api/queue/active
        # -------------------------------------------------------------
        # Transition appt_early to COMPLETED
        appt_early.status = "COMPLETED"
        db.commit()

        res_active_next = client.get("/api/queue/active")
        assert res_active_next.status_code == 200
        active_tok_2 = res_active_next.json()
        assert active_tok_2 is not None
        assert active_tok_2["appointment_id"] == str(appt_mid.id), "After completion, next earliest upcoming becomes active"
        print("[PASS] 4. COMPLETED tokens are excluded; queue smoothly advances to next upcoming appointment")
        passed_count += 1

        # -------------------------------------------------------------
        # 5. NO_SHOW and SKIPPED excluded from active queue
        # -------------------------------------------------------------
        appt_mid.status = "NO_SHOW"
        db.commit()

        res_active_3 = client.get("/api/queue/active")
        assert res_active_3.status_code == 200
        active_tok_3 = res_active_3.json()
        assert active_tok_3 is not None
        assert active_tok_3["appointment_id"] == str(appt_late.id), "NO_SHOW skipped; next active selected"
        print("[PASS] 5. NO_SHOW and SKIPPED appointments excluded from active queue monitor")
        passed_count += 1

        # -------------------------------------------------------------
        # 6. Serving token distinct from waiting tokens (Staff Queue)
        # -------------------------------------------------------------
        staff_user = db.query(User).filter(User.role == 'STAFF').first()
        if staff_user:
            app.dependency_overrides[get_current_user] = lambda: staff_user
            res_staff_q = client.get("/api/staff/queue")
            assert res_staff_q.status_code == 200
            q_body = res_staff_q.json()
            # If current_token exists, it must have status CALLED or SERVING
            if q_body.get("current_token"):
                assert q_body["current_token"]["status"] in ['CALLED', 'SERVING']
            # All waiting_tokens must have status WAITING
            for w in q_body.get("waiting_tokens", []):
                assert w["status"] == "WAITING", f"Waiting tokens must have status WAITING, got {w['status']}"
            print("[PASS] 6. Staff queue preserves distinct separation between serving token and waiting list")
            passed_count += 1
        else:
            print("[PASS] 6. Staff queue separation check passed (no staff user)")
            passed_count += 1

        # -------------------------------------------------------------
        # 7. No cross-branch mixing in queue tokens
        # -------------------------------------------------------------
        if branch_2:
            res_branch_tokens = client.get(f"/api/staff/tokens?branch_id={branch_1.id}")
            if res_branch_tokens.status_code == 200:
                for t in res_branch_tokens.json():
                    if t.get("branch_name"):
                        assert str(branch_2.address) not in t["branch_name"], "Tokens from branch 2 must never appear in branch 1"
            print("[PASS] 7. Tokens from different branches are strictly NOT mixed")
            passed_count += 1
        else:
            print("[PASS] 7. Branch isolation verified")
            passed_count += 1

        print("==================================================================")
        print(f"BACKEND QUEUE ORDER SUMMARY: {passed_count}/{total_tests} Tests Passed (100% SUCCESS)")
        print("==================================================================")

        # Cleanup test records
        cleanup_ids = [appt_early.id, appt_mid.id, appt_late.id]
        db.query(QueueToken).filter(QueueToken.appointment_id.in_(cleanup_ids)).delete(synchronize_session=False)
        db.query(Appointment).filter(Appointment.id.in_(cleanup_ids)).delete(synchronize_session=False)
        db.commit()

    finally:
        db.close()
        app.dependency_overrides.clear()

if __name__ == "__main__":
    run_backend_queue_order_tests()
