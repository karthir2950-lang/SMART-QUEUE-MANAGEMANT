import requests
import sys
import os
import time
from datetime import date, timedelta
import jwt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from app.db.database import SessionLocal
from app.models.domain import User, Appointment, QueueToken, QRToken, Branch, Service, Sector, Organization

BASE_URL = "http://127.0.0.1:8000"

def log(msg):
    print(msg, flush=True)

log("=================================================================")
log("QUEUELESS AI — END-TO-END BOOKING & TOKEN VERIFICATION SUITE")
log("=================================================================")

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "user@smartqueue.test").first()
    assert user is not None, "Test user user@smartqueue.test not found"
    user_id = user.id
    user_name = user.name
    user_email = user.email
    
    other_user = db.query(User).filter(User.role == 'USER', User.id != user.id).first()
    if not other_user:
        other_user = User(
            email="other_citizen_test@smartqueue.test",
            name="Other Citizen",
            role="USER",
            status="ACTIVE"
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
    other_user_id = other_user.id
    other_user_name = other_user.name
    other_user_email = other_user.email

def make_jwt(uid, email, name):
    payload = {
        "sub": str(uid),
        "email": email,
        "exp": time.time() + 3600,
        "user_metadata": {"full_name": name}
    }
    return jwt.encode(payload, "secret-test-key", algorithm="HS256")

user_token = make_jwt(user_id, user_email, user_name)
other_user_token = make_jwt(other_user_id, other_user_email, other_user_name)
user_headers = {"Authorization": f"Bearer {user_token}"}
other_headers = {"Authorization": f"Bearer {other_user_token}"}

# 1. Fetch available sector, organization, branch, service
res_sectors = requests.get(f"{BASE_URL}/api/sectors")
assert res_sectors.status_code == 200
sectors = res_sectors.json()
bank_sector = next((s for s in sectors if s['slug'] == 'bank'), sectors[0])
sector_id = bank_sector['id']

res_orgs = requests.get(f"{BASE_URL}/api/organizations?sector_id={sector_id}")
assert res_orgs.status_code == 200
orgs = res_orgs.json()
assert len(orgs) > 0, "No organizations found for sector"
org_id = orgs[0]['id']

res_branches = requests.get(f"{BASE_URL}/api/branches?organization_id={org_id}")
assert res_branches.status_code == 200
branches = res_branches.json()
assert len(branches) > 0, "No branches found for organization"
branch_id = branches[0]['id']

res_services = requests.get(f"{BASE_URL}/api/services?sector_id={sector_id}")
assert res_services.status_code == 200
services = res_services.json()
assert len(services) > 0, "No services found for sector"
service_id = services[0]['id']

# Pick a date 10 days in the future
test_date = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")

res_slots = requests.get(f"{BASE_URL}/api/appointments/available-slots", params={
    "branch_id": branch_id,
    "service_id": service_id,
    "appointment_date": test_date
})
assert res_slots.status_code == 200
slots = res_slots.json()
assert len(slots) > 0, f"No available slots on {test_date}"

# Find a slot that this user has not already booked
with SessionLocal() as db:
    booked_times = {
        str(a.appointment_time) for a in db.query(Appointment.appointment_time).filter(
            Appointment.user_id == user_id,
            Appointment.appointment_date == test_date,
            Appointment.status != 'CANCELLED'
        ).all()
    }

selected_time = next((s for s in slots if str(s) not in booked_times), slots[-1])

log(f"Target slot: Date {test_date}, Time {selected_time}, Service {services[0]['name']}")

# =========================================================================
# TEST 1: Book an appointment using the actual API
# =========================================================================
booking_payload = {
    "sector_id": sector_id,
    "organization_id": org_id,
    "branch_id": branch_id,
    "service_id": service_id,
    "appointment_date": test_date,
    "appointment_time": selected_time,
    "notes": "Automated E2E Verification Booking"
}

res_book = requests.post(
    f"{BASE_URL}/api/appointments",
    json=booking_payload,
    headers=user_headers
)
assert res_book.status_code == 200, f"Booking failed: {res_book.status_code} {res_book.text}"
booking_data = res_book.json()
appointment_id = booking_data.get("id")
token_number = booking_data.get("token_number")

assert appointment_id is not None, "Booking response missing appointment id"
assert token_number is not None, "Booking response missing token_number"
assert token_number.startswith("B-"), f"Expected B- prefix for bank, got {token_number}"
log(f"[PASS] 1 & 2. Booking API succeeded. Appointment ID: {appointment_id}, Token: {token_number}")

# =========================================================================
# TEST 2: Verify appointment exists in the real database
# =========================================================================
with SessionLocal() as db:
    db_appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    assert db_appt is not None, "Appointment not found in PostgreSQL database"
    assert str(db_appt.user_id) == str(user_id), "Appointment user_id does not match authenticated user"
    assert db_appt.status == "BOOKED", f"Expected BOOKED status, got {db_appt.status}"
    log(f"[PASS] 3. Verified appointment exists in Postgres with user_id={db_appt.user_id}")

    # =========================================================================
    # TEST 3: Verify token is generated and linked correctly in database
    # =========================================================================
    db_token = db.query(QueueToken).filter(QueueToken.appointment_id == appointment_id).first()
    assert db_token is not None, "QueueToken not found in PostgreSQL"
    assert db_token.token_number == token_number, f"DB token {db_token.token_number} != response {token_number}"
    assert db_token.status == "WAITING", f"Expected WAITING, got {db_token.status}"

    db_qr = db.query(QRToken).filter(QRToken.appointment_id == appointment_id).first()
    assert db_qr is not None, "QRToken not found in PostgreSQL"
    assert db_qr.queue_token_id == db_token.id, "QRToken queue_token_id mismatch"
    assert db_qr.secure_token is not None, "QRToken secure_token is None"
    qr_secure_token = db_qr.secure_token
    log(f"[PASS] 4. Verified QueueToken and QRToken linked in DB. Secure QR: {qr_secure_token[:8]}...")

# =========================================================================
# TEST 4: Open My Appointments (GET /api/appointments/user) and confirm token appears
# =========================================================================
res_my_appts = requests.get(f"{BASE_URL}/api/appointments/user", headers=user_headers)
assert res_my_appts.status_code == 200, f"My Appointments failed: {res_my_appts.status_code}"
my_appts = res_my_appts.json()
assert isinstance(my_appts, list), "Expected list of appointments"

target_appt = next((a for a in my_appts if str(a['id']) == str(appointment_id)), None)
assert target_appt is not None, "Newly booked appointment not in My Appointments response"
assert target_appt.get('token_number') == token_number, f"Expected {token_number}, got {target_appt.get('token_number')}"
assert target_appt.get('service_name') == services[0]['name']
assert target_appt.get('organization_name') == orgs[0]['name']
assert target_appt.get('status') == 'BOOKED'
log(f"[PASS] 5. My Appointments API returned appointment with Token Number: {target_appt.get('token_number')}")

# =========================================================================
# TEST 5: Refresh page (re-query API) and confirm the same token remains unchanged
# =========================================================================
res_refresh = requests.get(f"{BASE_URL}/api/appointments/user", headers=user_headers)
assert res_refresh.status_code == 200
refreshed_appt = next((a for a in res_refresh.json() if str(a['id']) == str(appointment_id)), None)
assert refreshed_appt['token_number'] == token_number, "Token changed after refreshing!"

with SessionLocal() as db:
    tokens_for_appt = db.query(QueueToken).filter(QueueToken.appointment_id == appointment_id).all()
    assert len(tokens_for_appt) == 1, f"Expected exactly 1 QueueToken in DB, got {len(tokens_for_appt)}"
log("[PASS] 6. Refreshing My Appointments returned identical token; no duplicate token created")

# =========================================================================
# TEST 6: Verify QR Code verification endpoint
# =========================================================================
res_qr_verify = requests.get(f"{BASE_URL}/api/queue/verify/{qr_secure_token}")
assert res_qr_verify.status_code == 200
qr_data = res_qr_verify.json()
assert qr_data.get('valid') is True, f"QR verification failed: {qr_data}"
assert qr_data.get('token_number') == token_number
assert qr_data.get('queue_status') == 'WAITING'
log(f"[PASS] 7. QR Code scan/verification verified valid for token {qr_data.get('token_number')}")

# =========================================================================
# TEST 7: Verify PDF Download containing ticket details
# =========================================================================
res_pdf = requests.get(f"{BASE_URL}/api/queue/token/{appointment_id}/pdf", headers=user_headers)
assert res_pdf.status_code == 200, f"PDF download failed: {res_pdf.status_code}"
assert res_pdf.headers.get("content-type") == "application/pdf"
assert res_pdf.content.startswith(b"%PDF-"), "Response does not start with valid PDF magic bytes (%PDF-)"
assert len(res_pdf.content) > 1000, "PDF content seems too small or empty"
content_disp = res_pdf.headers.get("content-disposition", "")
assert f"queue_token_{token_number}.pdf" in content_disp, f"Content-Disposition missing token filename: {content_disp}"
log(f"[PASS] 8. Downloaded PDF ticket ({len(res_pdf.content)} bytes, header: %PDF-) with filename queue_token_{token_number}.pdf")

# =========================================================================
# TEST 8: Verify cross-user authorization restriction (security)
# =========================================================================
# Another citizen user trying to view this specific appointment
res_unauth_view = requests.get(f"{BASE_URL}/api/appointments/{appointment_id}", headers=other_headers)
assert res_unauth_view.status_code == 403, f"Expected 403 Forbidden for cross-citizen appointment access, got {res_unauth_view.status_code}"

# Another citizen user trying to view token
res_unauth_token = requests.get(f"{BASE_URL}/api/queue/token/{appointment_id}", headers=other_headers)
assert res_unauth_token.status_code == 403, f"Expected 403 Forbidden for cross-citizen token access, got {res_unauth_token.status_code}"

# Another citizen user trying to download PDF
res_unauth_pdf = requests.get(f"{BASE_URL}/api/queue/token/{appointment_id}/pdf", headers=other_headers)
assert res_unauth_pdf.status_code == 403, f"Expected 403 Forbidden for cross-citizen PDF download, got {res_unauth_pdf.status_code}"

# Another citizen user's My Appointments must NOT include this appointment
res_other_appts = requests.get(f"{BASE_URL}/api/appointments/user", headers=other_headers)
assert res_other_appts.status_code == 200
other_appt_ids = [str(a['id']) for a in res_other_appts.json()]
assert str(appointment_id) not in other_appt_ids, "Cross-user leak: other citizen user saw private appointment!"
log("[PASS] 9. Cross-citizen isolation verified (403 on appointment, 403 on token, 403 on PDF, isolated list)")

# =========================================================================
# TEST 9: Test booking failure on duplicate / repeated submission
# =========================================================================
res_duplicate = requests.post(
    f"{BASE_URL}/api/appointments",
    json=booking_payload,
    headers=user_headers
)
assert res_duplicate.status_code == 409, f"Expected 409 Conflict on duplicate slot booking, got {res_duplicate.status_code}"
log("[PASS] 10. Repeated booking for same time slot correctly rejected with 409 Conflict")

# =========================================================================
# TEST 10: Calling POST /api/queue/token/{id} repeatedly is idempotent
# =========================================================================
res_token_repeat = requests.post(f"{BASE_URL}/api/queue/token/{appointment_id}", headers=user_headers)
assert res_token_repeat.status_code == 200
assert res_token_repeat.json()['token_number'] == token_number

with SessionLocal() as db:
    tokens_count = db.query(QueueToken).filter(QueueToken.appointment_id == appointment_id).count()
    assert tokens_count == 1
log("[PASS] 11. Repeated POST /api/queue/token/{id} is strictly idempotent (no duplicates)")

log("=================================================================")
log("ALL 11 TESTS PASSED! REAL BOOKING & TOKEN FLOW FULLY VERIFIED.")
log("=================================================================")
