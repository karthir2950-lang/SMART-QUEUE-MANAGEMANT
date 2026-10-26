import os
import sys
import uuid
sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Branch, Staff
from app.core.security import get_current_user

client = TestClient(app)
db = SessionLocal()

print("=========================================================")
print("RUNNING ROLE AND BRANCH AUTHORIZATION SECURITY TESTS")
print("=========================================================")

admin_user = db.query(User).filter(User.role == 'ADMIN').first()
staff_user = db.query(User).filter(User.role == 'STAFF').first()
reg_user = db.query(User).filter(User.role == 'USER').first()
staff_record = db.query(Staff).filter(Staff.user_id == staff_user.id, Staff.status == 'ACTIVE').first()

other_branch = db.query(Branch).filter(Branch.id != staff_record.branch_id).first()
assert other_branch, "Need at least two branches for branch isolation test"

# 1. Unauthenticated -> 401
app.dependency_overrides.clear()
res = client.get("/api/admin/dashboard/summary")
assert res.status_code == 401, f"Expected 401, got {res.status_code}"
print("[PASS] Unauthenticated request to /api/admin/dashboard/summary -> 401 Unauthorized")

res = client.get("/api/staff/dashboard/summary")
assert res.status_code == 401, f"Expected 401, got {res.status_code}"
print("[PASS] Unauthenticated request to /api/staff/dashboard/summary -> 401 Unauthorized")

# 2. USER -> Admin API: 403
app.dependency_overrides[get_current_user] = lambda: reg_user
res = client.get("/api/admin/dashboard/summary")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print("[PASS] Authenticated USER accessing /api/admin/dashboard/summary -> 403 Forbidden")

# 3. USER -> Staff API: 403
res = client.get("/api/staff/dashboard/summary")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print("[PASS] Authenticated USER accessing /api/staff/dashboard/summary -> 403 Forbidden")

# 4. STAFF -> Admin API: 403
app.dependency_overrides[get_current_user] = lambda: staff_user
res = client.get("/api/admin/dashboard/summary")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print("[PASS] Authenticated STAFF accessing /api/admin/dashboard/summary -> 403 Forbidden")

# 5. STAFF accessing own branch -> 200
res = client.get(f"/api/staff/dashboard/summary?branch_id={staff_record.branch_id}")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
print("[PASS] Authenticated STAFF accessing own branch summary -> 200 OK")

# 6. STAFF accessing other branch summary -> 403
res = client.get(f"/api/staff/dashboard/summary?branch_id={other_branch.id}")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print(f"[PASS] Authenticated STAFF accessing other branch summary (branch_id={other_branch.id}) -> 403 Forbidden")

# 7. STAFF accessing other branch appointments -> 403
res = client.get(f"/api/staff/appointments?branch_id={other_branch.id}")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print(f"[PASS] Authenticated STAFF accessing other branch appointments (branch_id={other_branch.id}) -> 403 Forbidden")

# 8. STAFF accessing other branch tokens -> 403
res = client.get(f"/api/staff/tokens?branch_id={other_branch.id}")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print(f"[PASS] Authenticated STAFF accessing other branch tokens (branch_id={other_branch.id}) -> 403 Forbidden")

# 9. STAFF accessing other branch queue -> 403
res = client.get(f"/api/staff/queue?branch_id={other_branch.id}")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print(f"[PASS] Authenticated STAFF accessing other branch queue (branch_id={other_branch.id}) -> 403 Forbidden")

# 10. ADMIN accessing admin summary -> 200
app.dependency_overrides[get_current_user] = lambda: admin_user
res = client.get("/api/admin/dashboard/summary")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
print("[PASS] Authenticated ADMIN accessing /api/admin/dashboard/summary -> 200 OK")

app.dependency_overrides.clear()
db.close()

print("=========================================================")
print("ALL ROLE AND BRANCH SECURITY TESTS PASSED (100% SPEC COMPLIANCE)!")
print("=========================================================")
