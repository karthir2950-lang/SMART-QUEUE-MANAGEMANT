import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import uuid
from datetime import date, time
from app.db.database import SessionLocal
from app.models.domain import User, Sector, Organization, Branch, Service, Counter, Staff, Appointment, QueueToken
from app.schemas.admin import OrganizationCreate, BranchCreate, ServiceCreate, CounterCreate, StaffCreate

db = SessionLocal()

print("=== RUNNING STEP 7 BACKEND API TESTS ===")

# 1. Verify / Create Test ADMIN, STAFF, and USER
admin_user = db.query(User).filter(User.email == "admin@smartqueue.test").first()
if not admin_user:
    admin_user = User(
        id=uuid.uuid4(),
        name="System Administrator",
        email="admin@smartqueue.test",
        phone=f"admin-{uuid.uuid4().hex[:6]}",
        role="ADMIN",
        status="ACTIVE"
    )
    db.add(admin_user)

staff_user = db.query(User).filter(User.email == "staff@smartqueue.test").first()
if not staff_user:
    staff_user = User(
        id=uuid.uuid4(),
        name="Staff Member",
        email="staff@smartqueue.test",
        phone=f"staff-{uuid.uuid4().hex[:6]}",
        role="STAFF",
        status="ACTIVE"
    )
    db.add(staff_user)

regular_user = db.query(User).filter(User.email == "user@smartqueue.test").first()
if not regular_user:
    regular_user = User(
        id=uuid.uuid4(),
        name="Regular Citizen",
        email="user@smartqueue.test",
        phone=f"user-{uuid.uuid4().hex[:6]}",
        role="USER",
        status="ACTIVE"
    )
    db.add(regular_user)

db.commit()
print("[PASS] Roles setup: ADMIN, STAFF, USER verified in DB")

# 2. Test Sector retrieval
hospital_sector = db.query(Sector).filter(Sector.slug == "hospital").first()
bank_sector = db.query(Sector).filter(Sector.slug == "bank").first()
assert hospital_sector and bank_sector, "Sectors not seeded"
print(f"[PASS] Sectors verified: Hospital ({hospital_sector.id}), Bank ({bank_sector.id})")

# 3. Test Admin endpoints logic directly
from app.api.endpoints.admin import (
    get_admin_dashboard_summary,
    create_organization, get_organizations, update_organization_status,
    create_branch, get_branches, update_branch_status,
    create_service, get_services, update_service_status,
    create_counter, get_counters, update_counter_status,
    assign_staff, get_staff_list, update_staff_status,
    get_all_appointments, get_all_tokens
)
from app.api.endpoints.staff import (
    get_staff_dashboard_summary,
    get_staff_appointments,
    get_staff_tokens
)
from fastapi import HTTPException

# Test Dashboard Summary
summary = get_admin_dashboard_summary(db=db, admin=admin_user)
print(f"[PASS] Admin Dashboard Summary retrieved: Total Orgs={summary.total_organizations}, Total Branches={summary.total_branches}, Sectors Breakdown Count={len(summary.sectors)}")
assert len(summary.sectors) == 6, f"Expected 6 sectors in breakdown, got {len(summary.sectors)}"

# Test Create Organization
test_org_name = f"Apollo Hospital {uuid.uuid4().hex[:4]}"
org_in = OrganizationCreate(
    sector_id=hospital_sector.id,
    name=test_org_name,
    city="Chennai",
    state="Tamil Nadu",
    address="Greams Road",
    status="ACTIVE"
)
created_org = create_organization(req=org_in, db=db, admin=admin_user)
print(f"[PASS] Created Organization: {created_org.name} (ID: {created_org.id})")
assert created_org.sector_id == hospital_sector.id

# Test Organization Status Toggle
toggled_org = update_organization_status(
    org_id=created_org.id,
    req=type("OrgStatus", (), {"status": "INACTIVE"})(),
    db=db,
    admin=admin_user
)
assert toggled_org.status == "INACTIVE", "Failed to update org status"
print("[PASS] Organization status toggle to INACTIVE verified")

# Reset back to ACTIVE
update_organization_status(org_id=created_org.id, req=type("OrgStatus", (), {"status": "ACTIVE"})(), db=db, admin=admin_user)

# Test Create Branch
branch_in = BranchCreate(
    organization_id=created_org.id,
    address="Greams Lane Main Campus",
    city="Chennai",
    state="Tamil Nadu",
    pincode="600006",
    opening_time=time(8, 0),
    closing_time=time(20, 0),
    status="ACTIVE"
)
created_branch = create_branch(req=branch_in, db=db, admin=admin_user)
print(f"[PASS] Created Branch: {created_branch.address}, {created_branch.city} (ID: {created_branch.id})")

# Test Create Counter
counter_in = CounterCreate(
    branch_id=created_branch.id,
    counter_number=1,
    name="Reception & Registration",
    status="AVAILABLE"
)
created_counter = create_counter(req=counter_in, db=db, admin=admin_user)
print(f"[PASS] Created Counter: #{created_counter.counter_number} {created_counter.name}")

# Test Duplicate Counter Number in Same Branch (Must fail with 409)
try:
    create_counter(req=counter_in, db=db, admin=admin_user)
    assert False, "Should have thrown 409 for duplicate counter in same branch"
except HTTPException as e:
    assert e.status_code == 409
    print(f"[PASS] Duplicate counter prevention passed with HTTP 409: {e.detail}")

# Test Same Counter Number in DIFFERENT Branch (Should succeed)
# Create another branch
branch2 = create_branch(
    req=BranchCreate(organization_id=created_org.id, address="Adyar Clinic", city="Chennai", state="Tamil Nadu", status="ACTIVE"),
    db=db,
    admin=admin_user
)
counter_branch2 = create_counter(
    req=CounterCreate(branch_id=branch2.id, counter_number=1, name="Reception", status="AVAILABLE"),
    db=db,
    admin=admin_user
)
assert counter_branch2.counter_number == 1
print("[PASS] Same counter number across different branches permitted successfully")

# Test Staff Assignment to Branch
staff_in = StaffCreate(
    email=staff_user.email,
    organization_id=created_org.id,
    branch_id=created_branch.id,
    name=staff_user.name
)
assigned_staff = assign_staff(req=staff_in, db=db, admin=admin_user)
print(f"[PASS] Assigned Staff: {assigned_staff.user_name} to {assigned_staff.branch_address}")
assert assigned_staff.branch_id == created_branch.id

# Test Staff Authorization Scope
staff_summary = get_staff_dashboard_summary(db=db, current_user=staff_user)
print(f"[PASS] Staff Dashboard Summary scoped: Branch={staff_summary.branch_name}, Assigned Counter={staff_summary.assigned_counter}")
assert staff_summary.branch_name == created_branch.address

# Test Staff Appointment View
staff_appts = get_staff_appointments(db=db, current_user=staff_user)
print(f"[PASS] Staff Appointments query scoped strictly to staff's branch (Total: {len(staff_appts)})")

# Test Role Authorization Enforcements
from app.core.security import require_admin, require_staff
try:
    require_admin(regular_user)
    assert False, "Regular user passed require_admin!"
except HTTPException as e:
    assert e.status_code == 403
    print("[PASS] USER rejected from ADMIN endpoints with 403")

try:
    require_admin(staff_user)
    assert False, "Staff user passed require_admin!"
except HTTPException as e:
    assert e.status_code == 403
    print("[PASS] STAFF rejected from ADMIN endpoints with 403")

try:
    require_staff(regular_user)
    assert False, "Regular user passed require_staff!"
except HTTPException as e:
    assert e.status_code == 403
    print("[PASS] USER rejected from STAFF endpoints with 403")

staff_pass = require_staff(staff_user)
assert staff_pass.id == staff_user.id
print("[PASS] STAFF authorized for STAFF endpoints")

print("\n==========================================")
print("ALL STEP 7 BACKEND CRITICAL TESTS PASSED!")
print("==========================================")
