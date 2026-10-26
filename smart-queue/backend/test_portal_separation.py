import requests
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

BASE_URL = "http://127.0.0.1:8000"

print("=================================================================")
print("RUNNING LIVE ENDPOINT AND ROLE AUTHORIZATION COMPREHENSIVE TESTS")
print("=================================================================")

# 1. Unauthenticated checks (Must return 401)
res_unauth_admin = requests.get(f"{BASE_URL}/api/admin/dashboard/summary")
assert res_unauth_admin.status_code == 401, f"Expected 401, got {res_unauth_admin.status_code}"
print("[PASS] 1. Unauthenticated GET /api/admin/dashboard/summary -> 401 Unauthorized")

res_unauth_staff = requests.get(f"{BASE_URL}/api/staff/dashboard/summary")
assert res_unauth_staff.status_code == 401, f"Expected 401, got {res_unauth_staff.status_code}"
print("[PASS] 2. Unauthenticated GET /api/staff/dashboard/summary -> 401 Unauthorized")

res_unauth_appts = requests.get(f"{BASE_URL}/api/staff/appointments")
assert res_unauth_appts.status_code == 401, f"Expected 401, got {res_unauth_appts.status_code}"
print("[PASS] 3. Unauthenticated GET /api/staff/appointments -> 401 Unauthorized")

res_unauth_tokens = requests.get(f"{BASE_URL}/api/staff/tokens")
assert res_unauth_tokens.status_code == 401, f"Expected 401, got {res_unauth_tokens.status_code}"
print("[PASS] 4. Unauthenticated GET /api/staff/tokens -> 401 Unauthorized")

res_unauth_queue = requests.get(f"{BASE_URL}/api/staff/queue")
assert res_unauth_queue.status_code == 401, f"Expected 401, got {res_unauth_queue.status_code}"
print("[PASS] 5. Unauthenticated GET /api/staff/queue -> 401 Unauthorized")

# 2. Public / Master data checks (Must return 200 with 6 sectors)
res_sectors = requests.get(f"{BASE_URL}/api/sectors")
assert res_sectors.status_code == 200, f"Expected 200, got {res_sectors.status_code}"
sectors = res_sectors.json()
assert len(sectors) == 6, f"Expected 6 sectors, got {len(sectors)}"
print(f"[PASS] 6. Public GET /api/sectors -> 200 OK (Exactly {len(sectors)} sectors verified)")

# 3. Create real JWT tokens for ADMIN, STAFF, USER to test live auth
import jwt
import time
from app.db.database import SessionLocal
from app.models.domain import User, Staff, Branch

with SessionLocal() as db:
    admin_user = db.query(User).filter(User.role == 'ADMIN').first()
    staff_user = db.query(User).filter(User.role == 'STAFF').first()
    reg_user = db.query(User).filter(User.role == 'USER').first()
    staff_record = db.query(Staff).filter(Staff.user_id == staff_user.id, Staff.status == 'ACTIVE').first()
    other_branch = db.query(Branch).filter(Branch.id != staff_record.branch_id).first()
    other_branch_id = other_branch.id

def make_token(u):
    payload = {
        "sub": str(u.id),
        "email": u.email,
        "exp": time.time() + 3600,
        "user_metadata": {"full_name": u.name}
    }
    return jwt.encode(payload, "secret-test-key", algorithm="HS256")

admin_jwt = make_token(admin_user)
staff_jwt = make_token(staff_user)
user_jwt = make_token(reg_user)

# 4. Authenticated USER role requesting Admin & Staff APIs (Must return 403)
res_user_on_admin = requests.get(
    f"{BASE_URL}/api/admin/dashboard/summary",
    headers={"Authorization": f"Bearer {user_jwt}"}
)
assert res_user_on_admin.status_code == 403, f"Expected 403, got {res_user_on_admin.status_code}"
print("[PASS] 7. Authenticated USER requesting /api/admin/dashboard/summary -> 403 Forbidden")

res_user_on_staff = requests.get(
    f"{BASE_URL}/api/staff/dashboard/summary",
    headers={"Authorization": f"Bearer {user_jwt}"}
)
assert res_user_on_staff.status_code == 403, f"Expected 403, got {res_user_on_staff.status_code}"
print("[PASS] 8. Authenticated USER requesting /api/staff/dashboard/summary -> 403 Forbidden")

res_user_on_me = requests.get(
    f"{BASE_URL}/api/auth/me",
    headers={"Authorization": f"Bearer {user_jwt}"}
)
assert res_user_on_me.status_code == 200, f"Expected 200, got {res_user_on_me.status_code}"
assert res_user_on_me.json()["role"] == "USER"
print("[PASS] 9. Authenticated USER GET /api/auth/me -> 200 OK (Role: USER from database)")

# 5. Authenticated STAFF role requesting Admin API (Must return 403)
res_staff_on_admin = requests.get(
    f"{BASE_URL}/api/admin/dashboard/summary",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_on_admin.status_code == 403, f"Expected 403, got {res_staff_on_admin.status_code}"
print("[PASS] 10. Authenticated STAFF requesting /api/admin/dashboard/summary -> 403 Forbidden")

# 6. Authenticated STAFF requesting Staff API for assigned branch (Must return 200)
res_staff_on_staff = requests.get(
    f"{BASE_URL}/api/staff/dashboard/summary",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_on_staff.status_code == 200, f"Expected 200, got {res_staff_on_staff.status_code}"
print(f"[PASS] 11. Authenticated STAFF requesting /api/staff/dashboard/summary -> 200 OK (Assigned: {res_staff_on_staff.json().get('assigned_counter')})")

res_staff_appts = requests.get(
    f"{BASE_URL}/api/staff/appointments",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_appts.status_code == 200, f"Expected 200, got {res_staff_appts.status_code}"
print(f"[PASS] 12. Authenticated STAFF requesting /api/staff/appointments -> 200 OK ({len(res_staff_appts.json())} branch appointments)")

res_staff_tokens = requests.get(
    f"{BASE_URL}/api/staff/tokens",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_tokens.status_code == 200, f"Expected 200, got {res_staff_tokens.status_code}"
print(f"[PASS] 13. Authenticated STAFF requesting /api/staff/tokens -> 200 OK ({len(res_staff_tokens.json())} branch tokens)")

# 7. Authenticated STAFF attempting unauthorized cross-branch access (Must return 403)
res_staff_cross_branch_summary = requests.get(
    f"{BASE_URL}/api/staff/dashboard/summary?branch_id={other_branch.id}",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_cross_branch_summary.status_code == 403, f"Expected 403, got {res_staff_cross_branch_summary.status_code}"
print(f"[PASS] 14. Authenticated STAFF cross-branch access /api/staff/dashboard/summary?branch_id={other_branch.id} -> 403 Forbidden")

res_staff_cross_branch_appts = requests.get(
    f"{BASE_URL}/api/staff/appointments?branch_id={other_branch.id}",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_cross_branch_appts.status_code == 403, f"Expected 403, got {res_staff_cross_branch_appts.status_code}"
print(f"[PASS] 15. Authenticated STAFF cross-branch access /api/staff/appointments?branch_id={other_branch.id} -> 403 Forbidden")

res_staff_cross_branch_tokens = requests.get(
    f"{BASE_URL}/api/staff/tokens?branch_id={other_branch.id}",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_cross_branch_tokens.status_code == 403, f"Expected 403, got {res_staff_cross_branch_tokens.status_code}"
print(f"[PASS] 16. Authenticated STAFF cross-branch access /api/staff/tokens?branch_id={other_branch.id} -> 403 Forbidden")

res_staff_cross_branch_queue = requests.get(
    f"{BASE_URL}/api/staff/queue?branch_id={other_branch.id}",
    headers={"Authorization": f"Bearer {staff_jwt}"}
)
assert res_staff_cross_branch_queue.status_code == 403, f"Expected 403, got {res_staff_cross_branch_queue.status_code}"
print(f"[PASS] 17. Authenticated STAFF cross-branch access /api/staff/queue?branch_id={other_branch.id} -> 403 Forbidden")

# 8. Authenticated ADMIN role requesting Admin APIs (Must return 200)
admin_endpoints = [
    ("/api/admin/dashboard/summary", "Admin Dashboard Summary"),
    ("/api/admin/organizations", "Organizations Management"),
    ("/api/admin/branches", "Branches Management"),
    ("/api/admin/services", "Services Management"),
    ("/api/admin/staff", "Staff Management"),
    ("/api/admin/counters", "Counters Management"),
    ("/api/admin/appointments", "Appointments Inspection"),
    ("/api/admin/tokens", "Queue Tokens Overview")
]

for ep, name in admin_endpoints:
    res = requests.get(f"{BASE_URL}{ep}", headers={"Authorization": f"Bearer {admin_jwt}"})
    assert res.status_code == 200, f"Expected 200 on {ep}, got {res.status_code}"
    print(f"[PASS] 18. Authenticated ADMIN GET {ep} -> 200 OK ({name})")

print("=================================================================")
print("ALL LIVE ENDPOINT & AUTHORIZATION TESTS PASSED WITH 100% SUCCESS!")
print("=================================================================")
