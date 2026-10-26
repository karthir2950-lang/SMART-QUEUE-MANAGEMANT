import os
import sys
import uuid
import time
from datetime import date, time as dt_time, timedelta

sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Branch, Organization, Counter, Staff, Sector, Service, Appointment, QueueToken, QueueEvent, Notification
from app.core.security import get_current_user

client = TestClient(app)
db = SessionLocal()

print("=========================================================")
print("RUNNING STEP 9: AI PREDICTION, NOTIFICATIONS & LIVE STREAM TESTS")
print("=========================================================")

passed = []
failed = []

def run_test(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"[PASS] {name}", flush=True)
    except Exception as e:
        import traceback
        try:
            db.rollback()
        except Exception:
            pass
        tb = traceback.format_exc()
        failed.append((name, tb))
        print(f"[FAIL] {name}:\n{tb}", flush=True)

# 1. SETUP TEST USERS & CONTEXT
admin_user = db.query(User).filter(User.role == 'ADMIN').first()
staff_user = db.query(User).filter(User.role == 'STAFF').first()
reg_user = db.query(User).filter(User.role == 'USER').first()

assert admin_user and staff_user and reg_user, "Required test users not found in DB"

# Verify staff assignment
staff_record = db.query(Staff).filter(Staff.user_id == staff_user.id, Staff.status == 'ACTIVE').first()
assert staff_record, "Staff member not assigned to any branch"
branch_id = staff_record.branch_id
org_id = staff_record.organization_id

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

counter.current_token_id = None
counter.status = "AVAILABLE"
db.commit()

service = db.query(Service).first()
sector = db.query(Sector).filter(Sector.id == service.sector_id).first()
today = date.today()

def create_test_token(client_user=reg_user):
    appt = Appointment(
        id=uuid.uuid4(),
        user_id=client_user.id,
        sector_id=sector.id,
        organization_id=org_id,
        branch_id=branch_id,
        service_id=service.id,
        appointment_date=today,
        appointment_time=dt_time(15, 30),
        status="BOOKED",
        notes="Step 9 Automated Test"
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    app.dependency_overrides[get_current_user] = lambda: client_user
    res = client.post(f"/api/queue/token/{appt.id}")
    assert res.status_code == 200, f"Token creation failed: {res.text}"
    token_data = res.json()
    token = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(token_data["id"])).first()
    return appt, token


# -------------------------------------------------------------
# TEST 1: AI Prediction Output Schema and Velocity Bounds
# -------------------------------------------------------------
def test_ai_prediction_engine():
    app.dependency_overrides[get_current_user] = lambda: reg_user
    appt, token = create_test_token()

    res = client.get(f"/api/queue/token/{appt.id}/prediction")
    assert res.status_code == 200, f"Prediction failed: {res.text}"
    data = res.json()

    assert data["token_id"] == str(token.id)
    assert data["token_number"] == token.token_number
    assert "people_ahead" in data
    assert "active_counters_count" in data
    assert "predicted_wait_minutes" in data
    assert "confidence_score" in data
    assert 50 <= data["confidence_score"] <= 100
    assert data["min_wait_minutes"] <= data["predicted_wait_minutes"] <= data["max_wait_minutes"]
    assert data["congestion_level"] in ["LOW", "MODERATE", "HIGH", "PEAK"]
    assert 0 <= data["turn_probability_next_15m"] <= 100
    assert len(data["ai_explanation"]) > 10

run_test("AI Prediction Engine returns structured dynamic wait, bounds, and confidence score", test_ai_prediction_engine)


# -------------------------------------------------------------
# TEST 2: Automated Notification on Token Generation
# -------------------------------------------------------------
def test_token_generated_notification():
    app.dependency_overrides[get_current_user] = lambda: reg_user
    appt, token = create_test_token()

    # Query notifications for reg_user
    res = client.get("/api/notifications")
    assert res.status_code == 200, f"Failed to get notifications: {res.text}"
    notifs = res.json()["notifications"]

    token_notif = next((n for n in notifs if n["appointment_id"] == str(appt.id) and n["type"] == "TOKEN_CREATED"), None)
    assert token_notif is not None, "TOKEN_CREATED notification not found for newly issued token"
    assert token.token_number in token_notif["title"] or token.token_number in token_notif["message"]

run_test("Automated TOKEN_CREATED notification is persisted and returned by /api/notifications", test_token_generated_notification)


# -------------------------------------------------------------
# TEST 3: Automated Calling Notification on Staff Call-Next
# -------------------------------------------------------------
def test_staff_call_notification():
    # Make sure counter is free
    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    appt, token = create_test_token()

    # Staff calls next
    app.dependency_overrides[get_current_user] = lambda: staff_user
    res_call = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res_call.status_code == 200, f"call-next failed: {res_call.text}"
    called_id = res_call.json()["id"]

    # Verify citizen received CALLED notification
    called_token = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(called_id)).first()
    if called_token and called_token.appointment:
        citizen_id = called_token.appointment.user_id
        citizen_user = db.query(User).filter(User.id == citizen_id).first()
        app.dependency_overrides[get_current_user] = lambda: citizen_user
        res_notif = client.get("/api/notifications")
        assert res_notif.status_code == 200
        notifs = res_notif.json()["notifications"]
        call_notif = next((n for n in notifs if n["appointment_id"] == str(called_token.appointment_id) and n["type"] == "CALLED"), None)
        assert call_notif is not None, "CALLED notification not found for called customer"
        assert f"Counter #{counter.counter_number}" in call_notif["message"]

    # Clean up token
    app.dependency_overrides[get_current_user] = lambda: staff_user
    client.post(f"/api/staff/queue/{called_id}/complete")

run_test("Staff call-next automatically dispatches CALLED notification with counter number", test_staff_call_notification)


# -------------------------------------------------------------
# TEST 4: Notification Read & Delete Lifecycle
# -------------------------------------------------------------
def test_notification_lifecycle_apis():
    app.dependency_overrides[get_current_user] = lambda: reg_user

    # Fetch notifications
    res = client.get("/api/notifications")
    assert res.status_code == 200
    items = res.json()["notifications"]
    assert len(items) > 0, "No notifications available for testing lifecycle"
    target = items[0]
    target_id = target["id"]

    # Mark as read
    res_read = client.patch(f"/api/notifications/{target_id}/read")
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # Mark all as read
    res_all = client.post("/api/notifications/read-all")
    assert res_all.status_code == 200
    assert "updated_count" in res_all.json()

    # Verify unread count is now 0
    res_after = client.get("/api/notifications")
    assert res_after.json()["unread_count"] == 0

    # Delete notification
    res_del = client.delete(f"/api/notifications/{target_id}")
    assert res_del.status_code == 200
    assert "deleted successfully" in res_del.json()["message"]

run_test("Notification lifecycle APIs (read, read-all, delete) function accurately", test_notification_lifecycle_apis)


# -------------------------------------------------------------
# TEST 5: Cross-User Security & Authorization
# -------------------------------------------------------------
def test_cross_user_security():
    other_user = db.query(User).filter(User.role == 'USER', User.id != reg_user.id).first()
    if not other_user:
        other_user = User(
            id=uuid.uuid4(),
            name="Other User Security Test",
            email=f"security_{uuid.uuid4().hex[:6]}@smartqueue.test",
            phone=f"sec_{uuid.uuid4().hex[:8]}",
            role="USER"
        )
        db.add(other_user)
        db.commit()

    # Create notification for reg_user
    app.dependency_overrides[get_current_user] = lambda: reg_user
    from app.services.notification_service import create_user_notification
    n = create_user_notification(db, reg_user.id, "TEST", "Test Title", "Test Message")
    db.commit()

    # Attempt to read or delete as other_user -> Must fail with 403
    app.dependency_overrides[get_current_user] = lambda: other_user
    res_read = client.patch(f"/api/notifications/{n.id}/read")
    assert res_read.status_code == 403, f"Expected 403 cross-user read, got {res_read.status_code}"

    res_del = client.delete(f"/api/notifications/{n.id}")
    assert res_del.status_code == 403, f"Expected 403 cross-user delete, got {res_del.status_code}"

run_test("Cross-user authorization blocks unauthorized notification access with HTTP 403", test_cross_user_security)


def test_sse_stream_connectivity():
    from app.services.broadcaster import broadcaster
    # 1. Test user live stream subscription and dispatch
    q = broadcaster.subscribe_user(str(reg_user.id))
    broadcaster.broadcast_sync_user(str(reg_user.id), {"event": "TEST_ALERT", "msg": "Turn approaching"})
    assert not q.empty(), "User broadcaster did not deliver event to subscriber queue"
    item = q.get_nowait()
    assert item["event"] == "TEST_ALERT"
    broadcaster.unsubscribe_user(str(reg_user.id), q)

    # 2. Test branch live stream subscription and dispatch
    bq = broadcaster.subscribe_branch(str(branch_id))
    broadcaster.broadcast_sync_branch(str(branch_id), {"event": "QUEUE_UPDATED", "action": "call_next"})
    assert not bq.empty(), "Branch broadcaster did not deliver event to subscriber queue"
    b_item = bq.get_nowait()
    assert b_item["event"] == "QUEUE_UPDATED"
    broadcaster.unsubscribe_branch(str(branch_id), bq)

run_test("Real-time stream broadcaster delivers live pub-sub events to subscriber queues", test_sse_stream_connectivity)


print("\n=========================================================")
print(f"STEP 9 TEST SUMMARY: {len(passed)} Passed, {len(failed)} Failed")
print("=========================================================")

db.close()

if failed:
    for name, err in failed:
        print(f"FAILED: {name} -> {err}")
    sys.exit(1)
else:
    print("ALL STEP 9 AI PREDICTION, NOTIFICATION & LIVE STREAM TESTS PASSED WITH 100% SUCCESS!")
