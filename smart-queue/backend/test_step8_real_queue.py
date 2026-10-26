import os
import sys
import uuid
from datetime import date, time, timedelta

sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Branch, Organization, Counter, Staff, Sector, Service, Appointment, QueueToken, QueueEvent
from app.core.security import get_current_user

client = TestClient(app)
db = SessionLocal()

print("=========================================================")
print("RUNNING STEP 8 REAL QUEUE ENGINE AUTOMATED TEST SUITE")
print("=========================================================")

import traceback

passed = []
failed = []

def run_test(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"[PASS] {name}", flush=True)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        tb = traceback.format_exc()
        failed.append((name, tb))
        print(f"[FAIL] {name}:\n{tb}", flush=True)

# 1. SETUP USERS & TEST BRANCH CONTEXT
admin_user = db.query(User).filter(User.role == 'ADMIN').first()
staff_user = db.query(User).filter(User.role == 'STAFF').first()
reg_user = db.query(User).filter(User.role == 'USER').first()

assert admin_user and staff_user and reg_user, "Required test users not found in DB"

# Verify staff assignment
staff_record = db.query(Staff).filter(Staff.user_id == staff_user.id, Staff.status == 'ACTIVE').first()
assert staff_record, "Staff member not assigned to any branch"
branch_id = staff_record.branch_id
org_id = staff_record.organization_id

# Verify/Create a Counter for this branch
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

# Reset counter state for clean test run
counter.current_token_id = None
counter.status = "AVAILABLE"
db.commit()

# Find service & sector for this org/branch
service = db.query(Service).first()
sector = db.query(Sector).filter(Sector.id == service.sector_id).first()

today = date.today()

# Helper to create test appointment & token
def create_test_appointment_and_token(appt_time=time(14, 0), client_user=reg_user):
    appt = Appointment(
        id=uuid.uuid4(),
        user_id=client_user.id,
        sector_id=sector.id,
        organization_id=org_id,
        branch_id=branch_id,
        service_id=service.id,
        appointment_date=today,
        appointment_time=appt_time,
        status="BOOKED",
        notes="Step 8 Automated Test"
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    # Issue queue token as client_user
    app.dependency_overrides[get_current_user] = lambda: client_user
    res = client.post(f"/api/queue/token/{appt.id}")
    assert res.status_code == 200, f"Failed to issue token: {res.text}"
    token_data = res.json()
    
    # Immediately restore staff_user override for staff actions
    app.dependency_overrides[get_current_user] = lambda: staff_user

    token = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(token_data["id"])).first()
    return appt, token


# -------------------------------------------------------------
# TEST 1: Unauthenticated and Role-Based Authorization
# -------------------------------------------------------------
def test_queue_authorization():
    app.dependency_overrides.clear()
    
    # 1. Unauthenticated -> 401
    res = client.get("/api/staff/queue")
    assert res.status_code == 401, f"Expected 401 unauthenticated, got {res.status_code}"
    
    res = client.post("/api/staff/queue/call-next")
    assert res.status_code == 401, f"Expected 401 unauthenticated, got {res.status_code}"

    # 2. Regular User -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: reg_user
    res = client.get("/api/staff/queue")
    assert res.status_code == 403, f"Expected 403 for user role, got {res.status_code}"

    res = client.post("/api/staff/queue/call-next")
    assert res.status_code == 403, f"Expected 403 for user role, got {res.status_code}"

    app.dependency_overrides[get_current_user] = lambda: staff_user

run_test("Queue endpoints enforce 401 unauthenticated and 403 non-staff access", test_queue_authorization)


# -------------------------------------------------------------
# TEST 2: GET /api/staff/queue returns valid structure
# -------------------------------------------------------------
def test_get_staff_queue():
    app.dependency_overrides[get_current_user] = lambda: staff_user
    res = client.get("/api/staff/queue")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "organization_name" in data
    assert "branch_name" in data
    assert "waiting_tokens" in data
    assert "waiting_count" in data
    assert "today_completed_count" in data

run_test("GET /api/staff/queue returns valid schema and counters", test_get_staff_queue)


# -------------------------------------------------------------
# TEST 3: Full Lifecycle: WAITING -> CALLED -> SERVING -> COMPLETED
# -------------------------------------------------------------
def test_full_queue_lifecycle():
    app.dependency_overrides[get_current_user] = lambda: staff_user
    
    # Clean counter state
    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    appt, token = create_test_appointment_and_token(appt_time=time(9, 30))
    token_id = str(token.id)
    assert token.status == "WAITING"

    # Step 3a: Call Next
    res_call = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res_call.status_code == 200, f"call-next failed: {res_call.text}"
    called_data = res_call.json()
    assert called_data["status"] == "CALLED"
    assert called_data["counter_id"] == str(counter.id)

    db.refresh(counter)
    assert str(counter.current_token_id) == called_data["id"]

    # Verify event recorded
    ev_called = db.query(QueueEvent).filter(QueueEvent.token_id == uuid.UUID(called_data["id"]), QueueEvent.event_type == "CALLED").first()
    assert ev_called, "QueueEvent for CALLED was not recorded"
    assert ev_called.previous_status == "WAITING"
    assert ev_called.new_status == "CALLED"
    assert ev_called.counter_id == counter.id

    # Step 3b: Start Serving
    target_token_id = called_data["id"]
    res_start = client.post(f"/api/staff/queue/{target_token_id}/start")
    assert res_start.status_code == 200, f"start serving failed: {res_start.text}"
    start_data = res_start.json()
    assert start_data["status"] == "SERVING"

    db.refresh(counter)
    assert counter.status == "BUSY"

    ev_serving = db.query(QueueEvent).filter(QueueEvent.token_id == uuid.UUID(target_token_id), QueueEvent.event_type == "SERVING").first()
    assert ev_serving, "QueueEvent for SERVING was not recorded"
    assert ev_serving.previous_status == "CALLED"
    assert ev_serving.new_status == "SERVING"

    # Step 3c: Complete
    res_comp = client.post(f"/api/staff/queue/{target_token_id}/complete")
    assert res_comp.status_code == 200, f"complete failed: {res_comp.text}"
    comp_data = res_comp.json()
    assert comp_data["status"] == "COMPLETED"

    # Verify counter freed
    db.refresh(counter)
    assert counter.current_token_id is None
    assert counter.status == "AVAILABLE"

    # Verify appointment marked COMPLETED
    db.expire_all()
    db_token = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(target_token_id)).first()
    assert db_token.status == "COMPLETED"
    assert db_token.appointment.status == "COMPLETED"

    # Verify QueueEvent for COMPLETED
    ev_comp = db.query(QueueEvent).filter(QueueEvent.token_id == uuid.UUID(target_token_id), QueueEvent.event_type == "COMPLETED").first()
    assert ev_comp, "QueueEvent for COMPLETED was not recorded"
    assert ev_comp.previous_status == "SERVING"
    assert ev_comp.new_status == "COMPLETED"

run_test("Full lifecycle (WAITING -> CALLED -> SERVING -> COMPLETED) with events & counter integrity", test_full_queue_lifecycle)


# -------------------------------------------------------------
# TEST 4: Skip Workflow: WAITING -> CALLED -> SKIPPED
# -------------------------------------------------------------
def test_skip_workflow():
    app.dependency_overrides[get_current_user] = lambda: staff_user
    
    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    appt, token = create_test_appointment_and_token(appt_time=time(10, 0))
    token_id = str(token.id)

    # Call it
    res_call = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res_call.status_code == 200
    called_id = res_call.json()["id"]

    # Skip it
    res_skip = client.post(f"/api/staff/queue/{called_id}/skip")
    assert res_skip.status_code == 200, f"skip failed: {res_skip.text}"
    skip_data = res_skip.json()
    assert skip_data["status"] == "SKIPPED"

    # Verify counter freed
    db.refresh(counter)
    assert counter.current_token_id is None
    assert counter.status == "AVAILABLE"

    # Verify QueueEvent
    ev_skip = db.query(QueueEvent).filter(QueueEvent.token_id == uuid.UUID(called_id), QueueEvent.event_type == "SKIPPED").first()
    assert ev_skip, "QueueEvent for SKIPPED not found"
    assert ev_skip.previous_status == "CALLED"
    assert ev_skip.new_status == "SKIPPED"

run_test("Skip path (CALLED -> SKIPPED) frees counter and records event", test_skip_workflow)


# -------------------------------------------------------------
# TEST 5: Mark No-Show Workflow: WAITING -> CALLED -> NO_SHOW
# -------------------------------------------------------------
def test_no_show_workflow():
    app.dependency_overrides[get_current_user] = lambda: staff_user
    
    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    appt, token = create_test_appointment_and_token(appt_time=time(10, 30))
    
    # Call it
    res_call = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res_call.status_code == 200
    called_id = res_call.json()["id"]

    # Mark No-Show
    res_ns = client.post(f"/api/staff/queue/{called_id}/no-show")
    assert res_ns.status_code == 200, f"no-show failed: {res_ns.text}"
    ns_data = res_ns.json()
    assert ns_data["status"] == "NO_SHOW"

    # Counter freed
    db.refresh(counter)
    assert counter.current_token_id is None
    assert counter.status == "AVAILABLE"

    # Appointment updated
    db.expire_all()
    t_obj = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(called_id)).first()
    assert t_obj.appointment.status == "NO_SHOW"

    # Event recorded
    ev_ns = db.query(QueueEvent).filter(QueueEvent.token_id == uuid.UUID(called_id), QueueEvent.event_type == "NO_SHOW").first()
    assert ev_ns, "QueueEvent for NO_SHOW not found"
    assert ev_ns.new_status == "NO_SHOW"

run_test("Mark No-Show path (CALLED -> NO_SHOW) frees counter, updates appt & records event", test_no_show_workflow)


# -------------------------------------------------------------
# TEST 6: Reject Invalid Status Transitions
# -------------------------------------------------------------
def test_invalid_transitions():
    app.dependency_overrides[get_current_user] = lambda: staff_user
    
    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    # 1. Start on WAITING token without calling first -> MUST FAIL (409)
    appt1, token1 = create_test_appointment_and_token(appt_time=time(11, 0))
    res = client.post(f"/api/staff/queue/{token1.id}/start")
    assert res.status_code == 409, f"Expected 409 starting WAITING token, got {res.status_code}"

    # 2. Complete on WAITING token -> MUST FAIL (409)
    res = client.post(f"/api/staff/queue/{token1.id}/complete")
    assert res.status_code == 409, f"Expected 409 completing WAITING token, got {res.status_code}"

    # 3. Call next to advance to CALLED, then START to SERVING
    res_call = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res_call.status_code == 200, f"call-next failed: {res_call.text}"
    called_id = res_call.json()["id"]
    res_start = client.post(f"/api/staff/queue/{called_id}/start")
    assert res_start.status_code == 200, f"start failed: {res_start.text}"

    # 4. Skip or No-Show on SERVING token -> MUST FAIL (409)
    res = client.post(f"/api/staff/queue/{called_id}/skip")
    assert res.status_code == 409, f"Expected 409 skipping SERVING token, got {res.status_code}"

    res = client.post(f"/api/staff/queue/{called_id}/no-show")
    assert res.status_code == 409, f"Expected 409 no-show SERVING token, got {res.status_code}"

    # 5. Cancel appointment while in SERVING status -> MUST FAIL (409)
    app.dependency_overrides[get_current_user] = lambda: reg_user
    db.expire_all()
    serving_token = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(called_id)).first()
    res = client.post(f"/api/appointments/{serving_token.appointment_id}/cancel")
    assert res.status_code == 409, f"Expected 409 cancelling SERVING appointment, got {res.status_code}"

    # 6. Complete the token
    app.dependency_overrides[get_current_user] = lambda: staff_user
    client.post(f"/api/staff/queue/{called_id}/complete")

    # 7. Start or Complete on COMPLETED token -> MUST FAIL (409)
    res = client.post(f"/api/staff/queue/{called_id}/start")
    assert res.status_code == 409, f"Expected 409 starting COMPLETED token, got {res.status_code}"

    res = client.post(f"/api/staff/queue/{called_id}/complete")
    assert res.status_code == 409, f"Expected 409 completing COMPLETED token, got {res.status_code}"

    # 8. Cancel appointment after COMPLETED -> MUST FAIL (409)
    app.dependency_overrides[get_current_user] = lambda: reg_user
    res = client.post(f"/api/appointments/{serving_token.appointment_id}/cancel")
    assert res.status_code == 409, f"Expected 409 cancelling COMPLETED appointment, got {res.status_code}"

    app.dependency_overrides[get_current_user] = lambda: staff_user

run_test("Invalid transitions (COMPLETED->WAITING, SERVING->CANCEL, etc.) strictly rejected with 409", test_invalid_transitions)


# -------------------------------------------------------------
# TEST 7: Counter Integrity & Double Serving Prevention
# -------------------------------------------------------------
def test_counter_double_serving_prevention():
    app.dependency_overrides[get_current_user] = lambda: staff_user

    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    # Create two waiting tokens
    appt1, tok1 = create_test_appointment_and_token(appt_time=time(11, 30))
    appt2, tok2 = create_test_appointment_and_token(appt_time=time(11, 45))

    # Call first token on counter
    res1 = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res1.status_code == 200

    # Call next AGAIN on SAME counter while first token is CALLED -> MUST FAIL WITH 409
    res2 = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res2.status_code == 409, f"Expected 409 for counter double-call, got {res2.status_code}: {res2.text}"
    assert "already serving token" in res2.text

    # Complete first token
    client.post(f"/api/staff/queue/{tok1.id}/complete")

    # Now calling next on same counter should succeed!
    res3 = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res3.status_code == 200
    assert res3.json()["id"] == str(tok2.id)

    # Clean up
    client.post(f"/api/staff/queue/{tok2.id}/complete")

run_test("Counter double-serving prevention blocks duplicate call-next with HTTP 409", test_counter_double_serving_prevention)


# -------------------------------------------------------------
# TEST 8: Deterministic Token Selection & Queue Positions
# -------------------------------------------------------------
def test_deterministic_queue_ordering():
    app.dependency_overrides[get_current_user] = lambda: staff_user

    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    # Create token for 15:00
    appt_later, tok_later = create_test_appointment_and_token(appt_time=time(15, 0))
    # Create token for 12:00
    appt_earlier, tok_earlier = create_test_appointment_and_token(appt_time=time(12, 0))

    # Query queue: tok_earlier should be position #1, tok_later should be position #2
    res = client.get("/api/staff/queue")
    assert res.status_code == 200
    waiting = res.json()["waiting_tokens"]

    # Earliest appointment must be called first
    res_call = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res_call.status_code == 200
    called_token_id = res_call.json()["id"]
    assert called_token_id == str(tok_earlier.id), "Earliest appointment was NOT selected first!"

    # Clean up
    client.post(f"/api/staff/queue/{tok_earlier.id}/complete")
    client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    client.post(f"/api/staff/queue/{tok_later.id}/complete")

run_test("Deterministic token selection (earliest appointment time ordered first)", test_deterministic_queue_ordering)


# -------------------------------------------------------------
# TEST 9: Empty Queue Handling
# -------------------------------------------------------------
def test_empty_queue_handling():
    app.dependency_overrides[get_current_user] = lambda: staff_user

    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    # Cancel/Complete any remaining waiting tokens in this branch for today
    waiting_all = (
        db.query(QueueToken)
        .join(Appointment)
        .filter(Appointment.branch_id == branch_id, Appointment.appointment_date == today, QueueToken.status == 'WAITING')
        .all()
    )
    for t in waiting_all:
        t.status = 'SKIPPED'
    db.commit()

    res = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res.status_code == 404, f"Expected 404 on empty queue, got {res.status_code}: {res.text}"
    assert "No waiting tokens available." in res.text

run_test("Empty queue handling returns HTTP 404 'No waiting tokens available.'", test_empty_queue_handling)


# -------------------------------------------------------------
# TEST 10: Cross-Branch Isolation & Security
# -------------------------------------------------------------
def test_branch_isolation_security():
    app.dependency_overrides[get_current_user] = lambda: staff_user

    # Find or create a branch different from staff's branch
    other_branch = db.query(Branch).filter(Branch.id != branch_id).first()
    if other_branch:
        # Create token in other branch
        other_appt = Appointment(
            id=uuid.uuid4(),
            user_id=reg_user.id,
            sector_id=sector.id,
            organization_id=other_branch.organization_id,
            branch_id=other_branch.id,
            service_id=service.id,
            appointment_date=today,
            appointment_time=time(16, 0),
            status="BOOKED"
        )
        db.add(other_appt)
        db.commit()
        db.refresh(other_appt)

        other_tok = QueueToken(
            id=uuid.uuid4(),
            appointment_id=other_appt.id,
            token_number="OTHER-1",
            status="WAITING"
        )
        db.add(other_tok)
        db.commit()
        db.refresh(other_tok)

        # Staff attempting to start, complete, or skip other branch's token -> MUST FAIL (403)
        res = client.post(f"/api/staff/queue/{other_tok.id}/start")
        assert res.status_code == 403, f"Expected 403 on cross-branch token start, got {res.status_code}"

        res = client.post(f"/api/staff/queue/{other_tok.id}/complete")
        assert res.status_code == 403, f"Expected 403 on cross-branch token complete, got {res.status_code}"

        res = client.post(f"/api/staff/queue/{other_tok.id}/skip")
        assert res.status_code == 403, f"Expected 403 on cross-branch token skip, got {res.status_code}"

run_test("Cross-branch isolation blocks unauthorized staff operations with HTTP 403", test_branch_isolation_security)


print("\n=========================================================")
print(f"STEP 8 TEST SUMMARY: {len(passed)} Passed, {len(failed)} Failed")
print("=========================================================")

db.close()

if failed:
    for name, err in failed:
        print(f"FAILED: {name} -> {err}")
    sys.exit(1)
else:
    print("ALL STEP 8 REAL QUEUE ENGINE TESTS PASSED WITH 100% SUCCESS!")
