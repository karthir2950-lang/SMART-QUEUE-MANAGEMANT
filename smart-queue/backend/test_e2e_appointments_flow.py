import requests
import time
from datetime import date, timedelta
from app.db.database import SessionLocal
from sqlalchemy import text
from app.models.domain import Appointment, QueueToken, QRToken

BASE_URL = "http://127.0.0.1:8000"
SUPABASE_URL = "https://argbqkkfoiuwiyfwhufp.supabase.co"
SUPABASE_KEY = "sb_publishable_pWNZxUFMnxHPc8cTr5QRzA_hDRLyKpv"

def get_auth_token(email, password):
    res = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password}
    )
    assert res.status_code == 200, f"Auth failed for {email}: {res.text}"
    return res.json()["access_token"]

def main():
    print("=== STARTING END-TO-END APPOINTMENTS VERIFICATION ===")

    # 0. Ensure empty_test_user@smartqueue.test email is confirmed
    db = SessionLocal()
    try:
        db.execute(text("UPDATE auth.users SET email_confirmed_at = NOW() WHERE email = 'empty_test_user@smartqueue.test'"))
        db.commit()
    finally:
        db.close()

    # 1. Log in User A (user@smartqueue.test)
    token_a = get_auth_token("user@smartqueue.test", "User@123456")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("[PASS] 1. User A authenticated successfully")

    # 2. Get active sector, org, branch, service
    sectors = requests.get(f"{BASE_URL}/api/sectors", headers=headers_a).json()
    assert len(sectors) > 0, "No active sectors found"
    sector_id = sectors[0]["id"]
    sector_name = sectors[0]["name"]

    orgs = requests.get(f"{BASE_URL}/api/organizations?sector_id={sector_id}", headers=headers_a).json()
    assert len(orgs) > 0, "No active organizations found"
    org_id = orgs[0]["id"]
    org_name = orgs[0]["name"]

    branches = requests.get(f"{BASE_URL}/api/branches?organization_id={org_id}", headers=headers_a).json()
    assert len(branches) > 0, "No active branches found"
    branch_id = branches[0]["id"]
    branch_name = f"{branches[0]['address']}, {branches[0]['city']}"

    services = requests.get(f"{BASE_URL}/api/services?sector_id={sector_id}", headers=headers_a).json()
    assert len(services) > 0, "No active services found"
    service_id = services[0]["id"]
    service_name = services[0]["name"]

    # 3. Find an available slot on a future date
    test_date = date.today() + timedelta(days=14)
    slots_res = requests.get(
        f"{BASE_URL}/api/appointments/available-slots",
        params={
            "branch_id": branch_id,
            "service_id": service_id,
            "appointment_date": test_date.isoformat()
        },
        headers=headers_a
    )
    assert slots_res.status_code == 200, f"Slots lookup failed: {slots_res.text}"
    available_slots = slots_res.json()
    assert len(available_slots) > 0, "No available slots found for future date"
    selected_time = available_slots[0]
    print(f"[PASS] 2. Selected slot: {test_date} at {selected_time} for {service_name} at {branch_name}")

    # 4. Book appointment
    payload = {
        "sector_id": sector_id,
        "organization_id": org_id,
        "branch_id": branch_id,
        "service_id": service_id,
        "appointment_date": test_date.isoformat(),
        "appointment_time": selected_time,
        "notes": "Automated End-to-End Test Appointment"
    }
    t_book = time.time()
    book_res = requests.post(f"{BASE_URL}/api/appointments", json=payload, headers=headers_a)
    assert book_res.status_code in [200, 201], f"Booking failed ({book_res.status_code}): {book_res.text}"
    booking_data = book_res.json()
    appt_id = booking_data["id"]
    token_num = booking_data.get("token_number")
    print(f"[PASS] 3. Appointment booked in {round(time.time() - t_book, 2)}s with ID: {appt_id}, Token: {token_num}")

    # 5. Verify database records directly
    with SessionLocal() as db:
        db_appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
        assert db_appt is not None, "Appointment not found in PostgreSQL database"
        assert db_appt.status == "BOOKED", f"Expected BOOKED, got {db_appt.status}"
        assert str(db_appt.branch_id) == str(branch_id), "Branch ID mismatch"
        assert str(db_appt.service_id) == str(service_id), "Service ID mismatch"

        db_token = db.query(QueueToken).filter(QueueToken.appointment_id == appt_id).first()
        assert db_token is not None, "QueueToken record missing in database"
        assert db_token.token_number == token_num, f"Token mismatch {db_token.token_number} vs {token_num}"

        db_qr = db.query(QRToken).filter(QRToken.appointment_id == appt_id).first()
        assert db_qr is not None, "QRToken record missing in database"
        print(f"[PASS] 4. Verified PostgreSQL records: Appointment, QueueToken ({db_token.token_number}), QRToken ({db_qr.secure_token[:8]}...)")

    # 6. Verify User A's My Appointments endpoint
    t_my = time.time()
    my_appts_res = requests.get(f"{BASE_URL}/api/appointments/user", headers=headers_a)
    assert my_appts_res.status_code == 200, f"User A list failed: {my_appts_res.status_code}"
    my_appts = my_appts_res.json()
    assert isinstance(my_appts, list), "Expected list response"
    found = next((a for a in my_appts if a["id"] == appt_id), None)
    assert found is not None, "Booked appointment missing from My Appointments response"
    assert found["token_number"] == token_num, "Token number mismatch in My Appointments"
    assert found["service_name"] == service_name, "Service name mismatch"
    assert found["organization_name"] == org_name, "Organization name mismatch"
    assert found["status"] == "BOOKED", "Status should be BOOKED"
    print(f"[PASS] 5. My Appointments endpoint returned in {round(time.time() - t_my, 2)}s with all correct appointment & token fields")

    # 7. Authenticate User B (empty_test_user@smartqueue.test)
    token_b = get_auth_token("empty_test_user@smartqueue.test", "User@123456")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print("[PASS] 6. User B authenticated successfully")

    # If User B has any previous active appointments from prior runs, cancel them via API
    user_b_initial = requests.get(f"{BASE_URL}/api/appointments/user", headers=headers_b).json()
    for b_appt in user_b_initial:
        if b_appt.get("status") == "BOOKED":
            c_res = requests.post(f"{BASE_URL}/api/appointments/{b_appt['id']}/cancel", headers=headers_b)
            assert c_res.status_code == 200, f"Failed to cancel User B prior appt: {c_res.text}"
            print(f"[INFO] Cancelled prior test appointment {b_appt['id']} for User B")

    # 8. Verify User B sees empty state
    user_b_res = requests.get(f"{BASE_URL}/api/appointments/user", headers=headers_b)
    assert user_b_res.status_code == 200, f"User B appointments failed: {user_b_res.status_code}"
    user_b_appts = user_b_res.json()
    assert isinstance(user_b_appts, list), "Expected list"
    assert len(user_b_appts) == 0, f"User B should have 0 active appointments, got {len(user_b_appts)}"
    print("[PASS] 7. User B receives 200 OK with empty list [] (clean empty state)")

    # 9. Verify User B CANNOT see User A's appointment
    unauth_appt_res = requests.get(f"{BASE_URL}/api/appointments/{appt_id}", headers=headers_b)
    assert unauth_appt_res.status_code == 403, f"Expected 403 Forbidden for User B, got {unauth_appt_res.status_code}"
    print(f"[PASS] 8. User B cross-user access to appointment {appt_id} correctly rejected with 403 Forbidden")

    # 10. Verify cancellation functionality
    cancel_res = requests.post(f"{BASE_URL}/api/appointments/{appt_id}/cancel", headers=headers_a)
    assert cancel_res.status_code == 200, f"Cancellation failed: {cancel_res.text}"
    
    # Check cancelled in DB
    with SessionLocal() as db:
        canc_appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
        assert canc_appt.status == "CANCELLED", f"Expected CANCELLED, got {canc_appt.status}"
        canc_token = db.query(QueueToken).filter(QueueToken.appointment_id == appt_id).first()
        assert canc_token.status == "CANCELLED", f"Expected token CANCELLED, got {canc_token.status}"
        print("[PASS] 9. Cancelled appointment confirmed in PostgreSQL database (status=CANCELLED)")

    # Check that cancelled appointment does NOT appear in My Appointments
    refresh_res = requests.get(f"{BASE_URL}/api/appointments/user", headers=headers_a)
    assert refresh_res.status_code == 200
    active_after_cancel = refresh_res.json()
    canc_in_list = next((a for a in active_after_cancel if a["id"] == appt_id), None)
    assert canc_in_list is None, f"Cancelled appointment {appt_id} MUST NOT appear in active My Appointments list"
    assert len(active_after_cancel) > 0, "Other active appointments must still appear in My Appointments"
    print(f"[PASS] 10. Verified cancelled appointment {appt_id} is completely hidden; {len(active_after_cancel)} active appointments still present")

    # Verify one user's cancellation cannot affect another user's appointments
    # Try cancelling another user's appointment as User B (must return 403)
    unauth_cancel = requests.post(f"{BASE_URL}/api/appointments/{active_after_cancel[0]['id']}/cancel", headers=headers_b)
    assert unauth_cancel.status_code == 403, f"Expected 403 for unauthorized cancellation, got {unauth_cancel.status_code}"
    print("[PASS] 11. Cross-user cancellation attempt strictly rejected with 403 Forbidden")

    print("\nALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
