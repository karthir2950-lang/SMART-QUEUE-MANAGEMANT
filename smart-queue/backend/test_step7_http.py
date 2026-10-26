import os
import sys
import uuid
sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Branch, Organization, Counter, Staff, Sector
from app.core.security import get_current_user

client = TestClient(app)
db = SessionLocal()

print("=========================================================")
print("RUNNING STEP 7 HTTP ENDPOINT & STATUS CODE TESTS")
print("=========================================================")

admin_user = db.query(User).filter(User.role == 'ADMIN').first()
staff_user = db.query(User).filter(User.role == 'STAFF').first()
reg_user = db.query(User).filter(User.role == 'USER').first()

assert admin_user, "No admin user found"
assert staff_user, "No staff user found"
assert reg_user, "No regular user found"

# 1. UNAUTHENTICATED REQUESTS (MUST RETURN 401)
app.dependency_overrides.clear()
res_unauth_admin = client.get("/api/admin/dashboard/summary")
assert res_unauth_admin.status_code == 401, f"Expected 401 for unauth admin, got {res_unauth_admin.status_code}"
print("[PASS] Unauthenticated GET /api/admin/dashboard/summary -> 401 Unauthorized")

res_unauth_staff = client.get("/api/staff/dashboard/summary")
assert res_unauth_staff.status_code == 401, f"Expected 401 for unauth staff, got {res_unauth_staff.status_code}"
print("[PASS] Unauthenticated GET /api/staff/dashboard/summary -> 401 Unauthorized")

# 2. USER ROLE AUTHORIZATION (MUST RETURN 403 ON ADMIN & STAFF)
app.dependency_overrides[get_current_user] = lambda: reg_user

res_user_admin = client.get("/api/admin/dashboard/summary")
assert res_user_admin.status_code == 403, f"Expected 403 for user accessing admin, got {res_user_admin.status_code}"
print("[PASS] USER role accessing /api/admin/dashboard/summary -> 403 Forbidden")

res_user_staff = client.get("/api/staff/dashboard/summary")
assert res_user_staff.status_code == 403, f"Expected 403 for user accessing staff, got {res_user_staff.status_code}"
print("[PASS] USER role accessing /api/staff/dashboard/summary -> 403 Forbidden")

res_user_sectors = client.get("/api/sectors")
assert res_user_sectors.status_code == 200
sectors_data = res_user_sectors.json()
assert len(sectors_data) == 6, f"Expected 6 sectors, got {len(sectors_data)}"
print(f"[PASS] Public/User GET /api/sectors -> 200 OK (Exactly {len(sectors_data)} sectors)")

# 3. STAFF ROLE AUTHORIZATION (MUST RETURN 403 ON ADMIN, 200 ON STAFF)
app.dependency_overrides[get_current_user] = lambda: staff_user

res_staff_admin = client.get("/api/admin/dashboard/summary")
assert res_staff_admin.status_code == 403, f"Expected 403 for staff accessing admin, got {res_staff_admin.status_code}"
print("[PASS] STAFF role accessing /api/admin/dashboard/summary -> 403 Forbidden")

res_staff_dashboard = client.get("/api/staff/dashboard/summary")
assert res_staff_dashboard.status_code == 200, f"Expected 200 for staff dashboard, got {res_staff_dashboard.status_code}: {res_staff_dashboard.text}"
print(f"[PASS] STAFF role GET /api/staff/dashboard/summary -> 200 OK (Branch: {res_staff_dashboard.json().get('branch_name')})")

res_staff_appts = client.get("/api/staff/appointments")
assert res_staff_appts.status_code == 200
print(f"[PASS] STAFF role GET /api/staff/appointments -> 200 OK ({len(res_staff_appts.json())} branch appointments)")

res_staff_tokens = client.get("/api/staff/tokens")
assert res_staff_tokens.status_code == 200
print(f"[PASS] STAFF role GET /api/staff/tokens -> 200 OK ({len(res_staff_tokens.json())} branch tokens)")

# 4. ADMIN ROLE AUTHORIZATION (MUST RETURN 200 ON ALL ADMIN APIS)
app.dependency_overrides[get_current_user] = lambda: admin_user

res_admin_summary = client.get("/api/admin/dashboard/summary")
assert res_admin_summary.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/dashboard/summary -> 200 OK (Total Orgs: {res_admin_summary.json().get('total_organizations')})")

res_admin_orgs = client.get("/api/admin/organizations")
assert res_admin_orgs.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/organizations -> 200 OK ({len(res_admin_orgs.json())} orgs)")

res_admin_branches = client.get("/api/admin/branches")
assert res_admin_branches.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/branches -> 200 OK ({len(res_admin_branches.json())} branches)")

res_admin_services = client.get("/api/admin/services")
assert res_admin_services.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/services -> 200 OK ({len(res_admin_services.json())} services)")

res_admin_staff = client.get("/api/admin/staff")
assert res_admin_staff.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/staff -> 200 OK ({len(res_admin_staff.json())} staff)")

res_admin_counters = client.get("/api/admin/counters")
assert res_admin_counters.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/counters -> 200 OK ({len(res_admin_counters.json())} counters)")

res_admin_appts = client.get("/api/admin/appointments")
assert res_admin_appts.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/appointments -> 200 OK ({len(res_admin_appts.json())} appts)")

res_admin_tokens = client.get("/api/admin/tokens")
assert res_admin_tokens.status_code == 200
print(f"[PASS] ADMIN role GET /api/admin/tokens -> 200 OK ({len(res_admin_tokens.json())} tokens)")

# 5. DUPLICATE COUNTER PREVENTION (MUST RETURN 409)
first_counter = db.query(Counter).first()
if first_counter:
    res_dup = client.post("/api/admin/counters", json={
        "branch_id": str(first_counter.branch_id),
        "counter_number": first_counter.counter_number,
        "name": "Duplicate Test Counter"
    })
    assert res_dup.status_code == 409, f"Expected 409 for duplicate counter, got {res_dup.status_code}"
    print(f"[PASS] Duplicate Counter POST /api/admin/counters -> 409 Conflict ({res_dup.json().get('detail')})")

# 6. MISSING RECORD (MUST RETURN 404)
fake_uuid = "00000000-0000-0000-0000-000000000000"
res_404_org = client.get(f"/api/admin/organizations/{fake_uuid}")
assert res_404_org.status_code == 404
print("[PASS] Non-existent organization GET -> 404 Not Found")

res_404_branch = client.get(f"/api/admin/branches/{fake_uuid}")
assert res_404_branch.status_code == 404
print("[PASS] Non-existent branch GET -> 404 Not Found")

res_404_service = client.get(f"/api/admin/services/{fake_uuid}")
assert res_404_service.status_code == 404
print("[PASS] Non-existent service GET -> 404 Not Found")

# Reset overrides
app.dependency_overrides.clear()
db.close()

print("\n=========================================================")
print("ALL STEP 7 HTTP TESTS PASSED WITH 100% SPEC COMPLIANCE!")
print("=========================================================")
