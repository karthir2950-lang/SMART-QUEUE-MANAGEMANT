import sys
import os
import requests
import datetime
from supabase import create_client

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from app.db.database import SessionLocal
from app.models.domain import User, Sector, Organization, Branch, Service, Counter, Appointment, QueueToken

BASE_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"
SUPABASE_URL = "https://argbqkkfoiuwiyfwhufp.supabase.co"
SUPABASE_KEY = "sb_publishable_pWNZxUFMnxHPc8cTr5QRzA_hDRLyKpv"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
results = []

def record(test_num, name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    results.append((test_num, name, status, details))
    print(f"[{status}] Test {test_num}: {name} {details}")

print("=================================================================")
print("QUEUELESS AI — ADMIN GOOGLE SIGN-IN & AUTHORIZATION TEST SUITE")
print("=================================================================")

# ----------------------------------------------------------------------
# 1. Real Google OAuth Account Verification & Session Establishment
# ----------------------------------------------------------------------
admin_token = None
admin_user_data = None

try:
    # Authenticate the real Google OAuth account registered as ADMIN
    auth_resp = sb.auth.sign_in_with_password({
        "email": "madheshr406@gmail.com",
        "password": "Admin@123456"
    })
    admin_token = auth_resp.session.access_token
    auth_user = auth_resp.user
    
    # Confirm this is genuinely a Google provider account in Supabase
    app_meta = auth_user.app_metadata or {}
    providers = app_meta.get("providers", [])
    primary_provider = app_meta.get("provider", "")
    assert "google" in providers or primary_provider == "google", f"Expected Google provider in metadata, got: {app_meta}"
    
    record(1, "Authenticate real Google account via Supabase", True, 
           f"(Email: {auth_user.email}, Provider: {primary_provider}, Providers: {providers})")
except Exception as e:
    record(1, "Authenticate real Google account via Supabase", False, str(e))

# ----------------------------------------------------------------------
# 2. Database Role Verification: Preserved as ADMIN, Never Downgraded
# ----------------------------------------------------------------------
try:
    # Query backend /api/auth/me with Bearer token
    me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
    admin_user_data = me_resp.json()
    
    assert admin_user_data["role"] == "ADMIN", f"Expected role ADMIN, got {admin_user_data['role']}"
    assert admin_user_data["status"] == "ACTIVE", f"Expected status ACTIVE, got {admin_user_data['status']}"
    assert admin_user_data["email"] == "madheshr406@gmail.com"
    
    # Check PostgreSQL database directly to confirm role is genuinely ADMIN in public.users
    db = SessionLocal()
    try:
        db_record = db.query(User).filter(User.email == "madheshr406@gmail.com").first()
        assert db_record is not None, "User record not found in public.users"
        assert db_record.role == "ADMIN", f"Database role in public.users is {db_record.role}, expected ADMIN"
    finally:
        db.close()
        
    record(2, "Confirm database role remains strictly ADMIN (never downgraded)", True,
           f"(DB Role: {db_record.role}, API Role: {admin_user_data['role']}, No mutation)")
except Exception as e:
    record(2, "Confirm database role remains strictly ADMIN (never downgraded)", False, str(e))

# ----------------------------------------------------------------------
# 3. Explicit Customer Profile Capability Linked to Admin Identity
# ----------------------------------------------------------------------
try:
    # Confirm capability fields returned by /api/auth/me
    assert "customer_profile_id" in admin_user_data, "customer_profile_id missing in profile"
    assert admin_user_data["customer_profile_id"] == admin_user_data["id"], "customer_profile_id must match primary user identity"
    assert admin_user_data.get("can_access_user_portal") is True, "can_access_user_portal must be True"
    
    record(3, "Explicit linked customer capability without duplicate identity", True,
           f"(Profile ID: {admin_user_data['id']}, Customer Linked ID: {admin_user_data['customer_profile_id']})")
except Exception as e:
    record(3, "Explicit linked customer capability without duplicate identity", False, str(e))

# ----------------------------------------------------------------------
# 4. User-Facing Sector Browsing & Availability Check by ADMIN
# ----------------------------------------------------------------------
first_sector = None
first_org = None
first_branch = None
first_service = None

try:
    # 4a. Fetch sectors
    sec_resp = requests.get(f"{BASE_URL}/api/sectors", headers={"Authorization": f"Bearer {admin_token}"})
    assert sec_resp.status_code == 200
    sectors = sec_resp.json()
    assert len(sectors) >= 6, f"Expected at least 6 sectors, got {len(sectors)}"
    first_sector = sectors[0]
    
    # 4b. Fetch organizations
    org_resp = requests.get(f"{BASE_URL}/api/organizations?sector_id={first_sector['id']}", 
                            headers={"Authorization": f"Bearer {admin_token}"})
    assert org_resp.status_code == 200
    orgs = org_resp.json()
    assert len(orgs) > 0, "No organizations found for sector"
    first_org = orgs[0]
    
    # 4c. Fetch branches
    br_resp = requests.get(f"{BASE_URL}/api/branches?organization_id={first_org['id']}", 
                           headers={"Authorization": f"Bearer {admin_token}"})
    assert br_resp.status_code == 200
    branches = br_resp.json()
    assert len(branches) > 0, "No branches found for organization"
    first_branch = branches[0]
    
    # 4d. Fetch services
    srv_resp = requests.get(f"{BASE_URL}/api/services?sector_id={first_sector['id']}", 
                            headers={"Authorization": f"Bearer {admin_token}"})
    assert srv_resp.status_code == 200
    services = srv_resp.json()
    assert len(services) > 0, "No services found for sector"
    first_service = services[0]
    
    # 4e. Available slots
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    slots_resp = requests.get(f"{BASE_URL}/api/appointments/available-slots", params={
        "branch_id": first_branch["id"],
        "service_id": first_service["id"],
        "appointment_date": tomorrow
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert slots_resp.status_code == 200
    slots = slots_resp.json()
    assert isinstance(slots, list)
    
    record(4, "ADMIN account can browse sectors, branches, services, and check slots", True,
           f"(Sector: {first_sector['name']}, Org: {first_org['name']}, Branch: {first_branch['city']})")
except Exception as e:
    record(4, "ADMIN account can browse sectors, branches, services, and check slots", False, str(e))

# ----------------------------------------------------------------------
# 5. User-Facing Appointment Booking & Queue Token Creation by ADMIN
# ----------------------------------------------------------------------
created_app_id = None
try:
    booking_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    booking_time = "14:30:00"
    
    # Cancel any previous conflicting test appointments for this user at this date/time
    db_clean = SessionLocal()
    try:
        prev = db_clean.query(Appointment).filter(
            Appointment.user_id == admin_user_data["id"],
            Appointment.appointment_date == booking_date,
            Appointment.appointment_time == booking_time,
            Appointment.status != 'CANCELLED'
        ).all()
        for p in prev:
            p.status = 'CANCELLED'
        db_clean.commit()
    finally:
        db_clean.close()

    # Book appointment
    book_resp = requests.post(f"{BASE_URL}/api/appointments", json={
        "sector_id": first_sector["id"],
        "organization_id": first_org["id"],
        "branch_id": first_branch["id"],
        "service_id": first_service["id"],
        "appointment_date": booking_date,
        "appointment_time": booking_time,
        "notes": "Admin test booking via User Dashboard"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert book_resp.status_code == 200, f"Booking failed ({book_resp.status_code}): {book_resp.text}"
    app_data = book_resp.json()
    created_app_id = app_data["id"]
    assert str(app_data["user_id"]) == str(admin_user_data["id"]), "Appointment user_id must match authenticated ADMIN"
    
    # Generate token
    token_resp = requests.post(f"{BASE_URL}/api/queue/token/{created_app_id}", 
                               headers={"Authorization": f"Bearer {admin_token}"})
    assert token_resp.status_code == 200, f"Token creation failed: {token_resp.text}"
    token_data = token_resp.json()
    assert "token_number" in token_data
    
    # Verify appointment appears in ADMIN's user-facing list
    my_appts_resp = requests.get(f"{BASE_URL}/api/appointments/user", 
                                 headers={"Authorization": f"Bearer {admin_token}"})
    assert my_appts_resp.status_code == 200
    my_appts = my_appts_resp.json()
    assert any(a["id"] == created_app_id for a in my_appts), "Created appointment not in user appointment list"
    
    # Clean up: cancel test appointment
    cancel_resp = requests.post(f"{BASE_URL}/api/appointments/{created_app_id}/cancel",
                                headers={"Authorization": f"Bearer {admin_token}"})
    assert cancel_resp.status_code == 200
    
    record(5, "ADMIN can book appointments, generate queue tokens, and manage appointments", True,
           f"(Appointment ID: {created_app_id}, Token: {token_data['token_number']}, Cancelled cleanly)")
except Exception as e:
    record(5, "ADMIN can book appointments, generate queue tokens, and manage appointments", False, str(e))

# ----------------------------------------------------------------------
# 6. Admin API Authorization: ADMIN account retains administrative privileges
# ----------------------------------------------------------------------
try:
    admin_summary = requests.get(f"{BASE_URL}/api/admin/dashboard/summary", 
                                 headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_summary.status_code == 200, f"Expected 200 for ADMIN, got {admin_summary.status_code}"
    summary_data = admin_summary.json()
    assert "total_organizations" in summary_data
    assert "total_branches" in summary_data
    
    record(6, "ADMIN privileges retained for backend Admin APIs (/api/admin/*)", True,
           f"(Total Orgs: {summary_data['total_organizations']}, Total Branches: {summary_data['total_branches']})")
except Exception as e:
    record(6, "ADMIN privileges retained for backend Admin APIs (/api/admin/*)", False, str(e))

# ----------------------------------------------------------------------
# 7. Backend Enforcement: Ordinary USER account strictly denied Admin APIs (403)
# ----------------------------------------------------------------------
try:
    user_resp = sb.auth.sign_in_with_password({
        "email": "user@smartqueue.test",
        "password": "User@123456"
    })
    regular_user_token = user_resp.session.access_token
    
    # Confirm role is USER
    user_me = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {regular_user_token}"})
    assert user_me.status_code == 200
    assert user_me.json()["role"] == "USER"
    
    # Must be 403 Forbidden on admin APIs
    denied_summary = requests.get(f"{BASE_URL}/api/admin/dashboard/summary", 
                                  headers={"Authorization": f"Bearer {regular_user_token}"})
    assert denied_summary.status_code == 403, f"Expected 403 Forbidden, got {denied_summary.status_code}"
    
    denied_orgs = requests.get(f"{BASE_URL}/api/admin/organizations", 
                               headers={"Authorization": f"Bearer {regular_user_token}"})
    assert denied_orgs.status_code == 403, f"Expected 403 Forbidden, got {denied_orgs.status_code}"
    
    record(7, "Ordinary USER accounts are strictly forbidden (403) from accessing Admin APIs", True,
           "(Backend enforced HTTP 403 Forbidden on /api/admin/*)")
except Exception as e:
    record(7, "Ordinary USER accounts are strictly forbidden (403) from accessing Admin APIs", False, str(e))

# ----------------------------------------------------------------------
# 8. Unauthenticated Access Protection: Returns 401 Unauthorized
# ----------------------------------------------------------------------
try:
    unauth_admin = requests.get(f"{BASE_URL}/api/admin/dashboard/summary")
    assert unauth_admin.status_code == 401, f"Expected 401, got {unauth_admin.status_code}"
    
    unauth_appts = requests.get(f"{BASE_URL}/api/appointments/user")
    assert unauth_appts.status_code == 401, f"Expected 401, got {unauth_appts.status_code}"
    
    record(8, "Unauthenticated requests strictly return HTTP 401 Unauthorized", True,
           "(Verified 401 on protected admin and user endpoints without credentials)")
except Exception as e:
    record(8, "Unauthenticated requests strictly return HTTP 401 Unauthorized", False, str(e))

# ----------------------------------------------------------------------
# 9. Frontend Route & Callback Code Audit
# ----------------------------------------------------------------------
try:
    frontend_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "../frontend"))
    
    # 9a. AuthCallback.jsx
    with open(os.path.join(frontend_dir, "src/pages/AuthCallback.jsx"), "r", encoding="utf-8") as f:
        auth_cb = f.read()
    assert "navigate('/user/dashboard', { replace: true });" in auth_cb, "AuthCallback must navigate to /user/dashboard"
    assert "navigate('/admin/dashboard'" not in auth_cb, "AuthCallback must not navigate to /admin/dashboard"
    assert "supabase.auth.signOut()" not in auth_cb or "prof.status !== 'ACTIVE'" in auth_cb, "signOut must not block active accounts"
    
    # 9b. Login.jsx
    with open(os.path.join(frontend_dir, "src/pages/Login.jsx"), "r", encoding="utf-8") as f:
        login_jsx = f.read()
    assert "provider === 'google'" in login_jsx, "Login.jsx must check google provider"
    
    # 9c. UserLayout.jsx
    with open(os.path.join(frontend_dir, "src/layouts/UserLayout.jsx"), "r", encoding="utf-8") as f:
        user_layout = f.read()
    assert "/admin/dashboard" not in user_layout, "UserLayout must not expose /admin/dashboard link"
    assert "Admin Portal" not in user_layout, "UserLayout must not have Admin Portal text in sidebar"
    
    # 9d. App.jsx
    with open(os.path.join(frontend_dir, "src/App.jsx"), "r", encoding="utf-8") as f:
        app_jsx = f.read()
    assert "allowedRoles={['USER', 'ADMIN', 'STAFF']}" in app_jsx, "App.jsx must allow ADMIN on /user"
    assert "allowedRoles={['ADMIN']}" in app_jsx, "App.jsx must restrict /admin to ADMIN"
    
    record(9, "Frontend route guards and OAuth callback verify intended routing and sidebar isolation", True,
           "(AuthCallback -> /user/dashboard; /user allows ADMIN; Admin portal isolated from user sidebar)")
except Exception as e:
    record(9, "Frontend route guards and OAuth callback verify intended routing and sidebar isolation", False, str(e))

print("\n=================================================================")
print("SUMMARY OF TEST RESULTS:")
print("=================================================================")
passed_count = sum(1 for _, _, s, _ in results if s == "PASS")
total_count = len(results)
for num, name, status, details in results:
    print(f"[{status}] Test {num}: {name} {details}")
print("=================================================================")
print(f"TOTAL: {passed_count}/{total_count} PASSED")
print("=================================================================")

if passed_count == total_count:
    sys.exit(0)
else:
    sys.exit(1)
