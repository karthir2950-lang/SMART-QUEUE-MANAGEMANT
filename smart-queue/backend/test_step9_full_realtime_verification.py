import os
import sys
import uuid
from datetime import date, time as dt_time, datetime, timezone

sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal, text
from app.models.domain import User, Branch, Organization, Counter, Staff, Sector, Service, Appointment, QueueToken, QueueEvent, Notification
from app.core.security import get_current_user

client = TestClient(app)
db = SessionLocal()

print("==================================================================")
print("RUNNING STEP 9 REAL-TIME QUEUE & NOTIFICATIONS VERIFICATION SUITE")
print("==================================================================")

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

# Context setup
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

# -------------------------------------------------------------
# TEST 1: Booking Confirmation & Token Generated Notifications
# -------------------------------------------------------------
def test_booking_and_token_notifications():
    app.dependency_overrides[get_current_user] = lambda: reg_user_a

    # Ensure idempotency by cancelling any prior test appointment at this slot
    db.query(Appointment).filter(
        Appointment.user_id == reg_user_a.id,
        Appointment.appointment_date == today,
        Appointment.appointment_time == dt_time(16, 45)
    ).update({"status": "CANCELLED"})
    db.commit()

    payload = {
        "sector_id": str(sector.id),
        "organization_id": str(org_id),
        "branch_id": str(branch_id),
        "service_id": str(service.id),
        "appointment_date": str(today),
        "appointment_time": "16:45:00",
        "notes": "Realtime notification test"
    }
    res = client.post("/api/appointments", json=payload)
    assert res.status_code == 200, f"Booking failed: {res.text}"
    appt_data = res.json()
    appt_id = appt_data["id"]

    # Verify notifications in DB for user A
    notifs_res = client.get("/api/notifications")
    assert notifs_res.status_code == 200
    notif_list = notifs_res.json()["notifications"]

    # Check for APPOINTMENT_BOOKED
    booked_notif = next((n for n in notif_list if n["appointment_id"] == appt_id and n["type"] == "APPOINTMENT_BOOKED"), None)
    assert booked_notif is not None, "APPOINTMENT_BOOKED notification was not created"
    assert service.name in booked_notif["title"]

    # Check for TOKEN_CREATED
    token_notif = next((n for n in notif_list if n["appointment_id"] == appt_id and n["type"] == "TOKEN_CREATED"), None)
    assert token_notif is not None, "TOKEN_CREATED notification was not created"
    assert appt_data["token_number"] in token_notif["title"] or appt_data["token_number"] in token_notif["message"]

run_test("Booking an appointment automatically generates APPOINTMENT_BOOKED and TOKEN_CREATED notifications", test_booking_and_token_notifications)


# -------------------------------------------------------------
# TEST 2: Appointment Cancellation Notification
# -------------------------------------------------------------
def test_cancellation_notification():
    app.dependency_overrides[get_current_user] = lambda: reg_user_a

    # Create fresh appointment to cancel
    db.query(Appointment).filter(
        Appointment.user_id == reg_user_a.id,
        Appointment.appointment_date == today,
        Appointment.appointment_time == dt_time(17, 15)
    ).update({"status": "CANCELLED"})
    db.commit()

    appt = Appointment(
        id=uuid.uuid4(),
        user_id=reg_user_a.id,
        sector_id=sector.id,
        organization_id=org_id,
        branch_id=branch_id,
        service_id=service.id,
        appointment_date=today,
        appointment_time=dt_time(17, 15),
        status="BOOKED",
        notes="Cancel test"
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    # Cancel
    res_cancel = client.post(f"/api/appointments/{appt.id}/cancel")
    assert res_cancel.status_code == 200, f"Cancel failed: {res_cancel.text}"

    # Verify APPOINTMENT_CANCELLED notification
    notifs_res = client.get("/api/notifications")
    notif_list = notifs_res.json()["notifications"]
    cancel_notif = next((n for n in notif_list if n["appointment_id"] == str(appt.id) and n["type"] == "APPOINTMENT_CANCELLED"), None)
    assert cancel_notif is not None, "APPOINTMENT_CANCELLED notification was not created"
    assert "Cancelled" in cancel_notif["title"]

run_test("Cancelling an appointment dispatches an APPOINTMENT_CANCELLED notification", test_cancellation_notification)


# -------------------------------------------------------------
# TEST 3: Token Status Transitions (WAITING -> CALLED -> SERVING -> COMPLETED)
# -------------------------------------------------------------
def test_token_status_transitions():
    counter.current_token_id = None
    counter.status = "AVAILABLE"
    db.commit()

    db.query(Appointment).filter(
        Appointment.user_id == reg_user_a.id,
        Appointment.appointment_date == today,
        Appointment.appointment_time == dt_time(17, 30)
    ).update({"status": "CANCELLED"})
    db.commit()

    appt = Appointment(
        id=uuid.uuid4(),
        user_id=reg_user_a.id,
        sector_id=sector.id,
        organization_id=org_id,
        branch_id=branch_id,
        service_id=service.id,
        appointment_date=today,
        appointment_time=dt_time(17, 30),
        status="BOOKED"
    )
    db.add(appt)
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: reg_user_a
    res_tok = client.post(f"/api/queue/token/{appt.id}")
    assert res_tok.status_code == 200
    token_id = res_tok.json()["id"]

    # 1. Staff Call-Next
    app.dependency_overrides[get_current_user] = lambda: staff_user
    res_call = client.post(f"/api/staff/queue/call-next?counter_id={counter.id}")
    assert res_call.status_code == 200, f"call-next failed: {res_call.text}"
    called_id = res_call.json()["id"]
    assert res_call.json()["status"] == "CALLED"

    # 2. Staff Start Serving
    res_start = client.post(f"/api/staff/queue/{called_id}/start")
    assert res_start.status_code == 200, f"start failed: {res_start.text}"
    assert res_start.json()["status"] == "SERVING"

    # 3. Staff Complete
    res_comp = client.post(f"/api/staff/queue/{called_id}/complete")
    assert res_comp.status_code == 200, f"complete failed: {res_comp.text}"
    assert res_comp.json()["status"] == "COMPLETED"

    # Check that CALLED, SERVING, and COMPLETED notifications exist for the called customer
    called_token = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(called_id)).first()
    assert called_token and called_token.appointment
    citizen_user = db.query(User).filter(User.id == called_token.appointment.user_id).first()
    app.dependency_overrides[get_current_user] = lambda: citizen_user
    notifs = client.get("/api/notifications").json()["notifications"]
    called_n = next((n for n in notifs if n["appointment_id"] == str(called_token.appointment_id) and n["type"] == "CALLED"), None)
    serving_n = next((n for n in notifs if n["appointment_id"] == str(called_token.appointment_id) and n["type"] == "SERVING"), None)
    completed_n = next((n for n in notifs if n["appointment_id"] == str(called_token.appointment_id) and n["type"] == "COMPLETED"), None)

    assert called_n is not None, "CALLED notification missing"
    assert serving_n is not None, "SERVING notification missing"
    assert completed_n is not None, "COMPLETED notification missing"

run_test("Queue transitions (WAITING -> CALLED -> SERVING -> COMPLETED) record valid statuses and notifications", test_token_status_transitions)


# -------------------------------------------------------------
# TEST 4: Cross-User Security & Authorization Boundaries
# -------------------------------------------------------------
def test_cross_user_isolation():
    # Create notification for User A
    from app.services.notification_service import create_user_notification
    notif_a = create_user_notification(db, reg_user_a.id, "SEC_TEST", "Private Alert", "Secret Info User A")
    db.commit()

    # Create appointment for User A
    db.query(Appointment).filter(
        Appointment.user_id == reg_user_a.id,
        Appointment.appointment_date == today,
        Appointment.appointment_time == dt_time(18, 0)
    ).update({"status": "CANCELLED"})
    db.commit()

    appt_a = Appointment(
        id=uuid.uuid4(),
        user_id=reg_user_a.id,
        sector_id=sector.id,
        organization_id=org_id,
        branch_id=branch_id,
        service_id=service.id,
        appointment_date=today,
        appointment_time=dt_time(18, 0),
        status="BOOKED"
    )
    db.add(appt_a)
    db.commit()

    # User B attempts to access User A's notification -> MUST return 403
    app.dependency_overrides[get_current_user] = lambda: reg_user_b
    res_read = client.patch(f"/api/notifications/{notif_a.id}/read")
    assert res_read.status_code == 403, f"Expected 403, got {res_read.status_code}"

    res_del = client.delete(f"/api/notifications/{notif_a.id}")
    assert res_del.status_code == 403, f"Expected 403, got {res_del.status_code}"

    # User B attempts to access User A's appointment -> MUST return 403
    res_appt = client.get(f"/api/appointments/{appt_a.id}")
    assert res_appt.status_code == 403, f"Expected 403, got {res_appt.status_code}"

    res_cancel = client.post(f"/api/appointments/{appt_a.id}/cancel")
    assert res_cancel.status_code == 403, f"Expected 403, got {res_cancel.status_code}"

    # User B's notification list does NOT include User A's notification
    b_notifs = client.get("/api/notifications").json()["notifications"]
    assert not any(n["id"] == str(notif_a.id) for n in b_notifs), "User B saw User A's notification in list!"

run_test("Cross-user authorization strictly prevents User B from accessing User A's notifications & appointments", test_cross_user_isolation)


# -------------------------------------------------------------
# TEST 5: Role-Based Authorization for Privileged Queue Actions
# -------------------------------------------------------------
def test_role_based_permissions():
    # Regular user attempting staff call-next -> 403
    app.dependency_overrides[get_current_user] = lambda: reg_user_a
    res = client.post("/api/staff/queue/call-next")
    assert res.status_code == 403

    # Unauthenticated user attempting notifications -> 401
    app.dependency_overrides.clear()
    res_unauth = client.get("/api/notifications")
    assert res_unauth.status_code == 401

run_test("Role-based permissions block unauthorized users from Staff queue operations and unauthenticated access", test_role_based_permissions)


# -------------------------------------------------------------
# TEST 6: Notification Read Lifecycle & Unread Count Tracking
# -------------------------------------------------------------
def test_unread_count_lifecycle():
    app.dependency_overrides[get_current_user] = lambda: reg_user_a

    # Get baseline notifications
    res = client.get("/api/notifications")
    data = res.json()
    items = data["notifications"]
    unread = data["unread_count"]
    assert unread >= 0

    if items:
        first_item = items[0]
        # Mark as read
        res_read = client.patch(f"/api/notifications/{first_item['id']}/read")
        assert res_read.status_code == 200
        assert res_read.json()["is_read"] is True

    # Mark all read
    res_all = client.post("/api/notifications/read-all")
    assert res_all.status_code == 200

    # Verify unread count is now 0
    res_after = client.get("/api/notifications")
    assert res_after.json()["unread_count"] == 0

run_test("Notification read lifecycle and unread counter update accurately", test_unread_count_lifecycle)


# -------------------------------------------------------------
# TEST 7: Supabase PostgreSQL RLS & Realtime Publication Verification
# -------------------------------------------------------------
def test_rls_and_realtime_publication():
    with db.connection() as conn:
        # Verify RLS enabled on tables
        rls_res = conn.execute(text("""
            SELECT relname, relrowsecurity 
            FROM pg_class 
            JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace 
            WHERE pg_namespace.nspname = 'public' 
              AND relname IN ('notifications', 'appointments', 'queue_tokens');
        """)).fetchall()

        rls_map = {row[0]: row[1] for row in rls_res}
        assert rls_map.get("notifications") is True, "notifications table does not have RLS enabled"
        assert rls_map.get("appointments") is True, "appointments table does not have RLS enabled"
        assert rls_map.get("queue_tokens") is True, "queue_tokens table does not have RLS enabled"

        # Verify Realtime publication includes tables
        pub_res = conn.execute(text("""
            SELECT tablename 
            FROM pg_publication_tables 
            WHERE pubname = 'supabase_realtime';
        """)).fetchall()
        pub_tables = {row[0] for row in pub_res}
        assert "notifications" in pub_tables, "notifications not in supabase_realtime publication"
        assert "appointments" in pub_tables, "appointments not in supabase_realtime publication"
        assert "queue_tokens" in pub_tables, "queue_tokens not in supabase_realtime publication"

run_test("PostgreSQL tables have Row Level Security (RLS) enabled and are published in supabase_realtime", test_rls_and_realtime_publication)


print("\n==================================================================")
print(f"VERIFICATION SUMMARY: {len(passed)} Passed, {len(failed)} Failed")
print("==================================================================")

db.close()

if failed:
    for name, err in failed:
        print(f"FAILED: {name} -> {err}")
    sys.exit(1)
else:
    print("ALL STEP 9 REAL-TIME QUEUE & NOTIFICATIONS VERIFICATION TESTS PASSED WITH 100% SUCCESS!")
