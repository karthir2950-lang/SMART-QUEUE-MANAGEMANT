import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import uuid
from datetime import date, time
from fastapi import HTTPException
from app.db.database import SessionLocal
from app.models.domain import (
    User, Sector, Organization, Branch, Service, Counter, Staff,
    Appointment, QueueToken
)
from app.schemas.admin import (
    OrganizationCreate, OrganizationUpdate, OrganizationStatusUpdate,
    BranchCreate, BranchUpdate, BranchStatusUpdate,
    ServiceCreate, ServiceUpdate, ServiceStatusUpdate,
    CounterCreate, CounterUpdate, CounterStatusUpdate,
    StaffCreate, StaffUpdate, StaffStatusUpdate
)
from app.api.endpoints.admin import (
    get_admin_dashboard_summary,
    get_organizations, create_organization, get_organization_by_id, update_organization, update_organization_status,
    get_branches, create_branch, get_branch_by_id, update_branch, update_branch_status,
    get_services, create_service, get_service_by_id, update_service, update_service_status,
    get_counters, create_counter, get_counter_by_id, update_counter, update_counter_status,
    get_staff_list, assign_staff, get_staff_by_id, update_staff, update_staff_status,
    get_all_appointments, get_all_tokens
)
from app.api.endpoints.staff import (
    get_staff_dashboard_summary,
    get_staff_appointments,
    get_staff_tokens
)
from app.core.security import require_admin, require_staff, require_user

db = SessionLocal()
passed_tests = []
failed_tests = []

def run_test(name, fn):
    try:
        fn()
        passed_tests.append(name)
        print(f"[PASS] {name}")
    except Exception as e:
        failed_tests.append((name, str(e)))
        print(f"[FAIL] {name}: {e}")

print("=========================================================")
print("RUNNING COMPREHENSIVE STEP 7 VERIFICATION TEST SUITE")
print("=========================================================")

# -----------------------------------------------------------------
# 1. SETUP USERS FOR TESTING
# -----------------------------------------------------------------
admin_user = db.query(User).filter(User.email == "admin@smartqueue.test").first()
if not admin_user:
    admin_user = User(
        id=uuid.uuid4(),
        name="System Admin",
        email="admin@smartqueue.test",
        phone=f"admin-{uuid.uuid4().hex[:6]}",
        role="ADMIN",
        status="ACTIVE"
    )
    db.add(admin_user)

staff_user_1 = db.query(User).filter(User.email == "staff1@smartqueue.test").first()
if not staff_user_1:
    staff_user_1 = User(
        id=uuid.uuid4(),
        name="Staff Member Alpha",
        email="staff1@smartqueue.test",
        phone=f"staff1-{uuid.uuid4().hex[:6]}",
        role="STAFF",
        status="ACTIVE"
    )
    db.add(staff_user_1)

staff_user_2 = db.query(User).filter(User.email == "staff2@smartqueue.test").first()
if not staff_user_2:
    staff_user_2 = User(
        id=uuid.uuid4(),
        name="Staff Member Beta",
        email="staff2@smartqueue.test",
        phone=f"staff2-{uuid.uuid4().hex[:6]}",
        role="STAFF",
        status="ACTIVE"
    )
    db.add(staff_user_2)

reg_user = db.query(User).filter(User.email == "regular@smartqueue.test").first()
if not reg_user:
    reg_user = User(
        id=uuid.uuid4(),
        name="Regular Citizen",
        email="regular@smartqueue.test",
        phone=f"reg-{uuid.uuid4().hex[:6]}",
        role="USER",
        status="ACTIVE"
    )
    db.add(reg_user)

db.commit()

# -----------------------------------------------------------------
# 2. SECTORS INTEGRITY (MUST BE EXACTLY 6 STANDARD SECTORS)
# -----------------------------------------------------------------
def test_six_sectors():
    sectors = db.query(Sector).all()
    assert len(sectors) == 6, f"Expected exactly 6 sectors, found {len(sectors)}"
    slugs = {s.slug for s in sectors}
    expected = {'hospital', 'bank', 'restaurant', 'government-office', 'retail', 'supermarket'}
    assert slugs == expected, f"Sector slugs mismatch: {slugs} != {expected}"

run_test("Database contains exactly 6 standard sectors with correct slugs", test_six_sectors)

hospital_sector = db.query(Sector).filter(Sector.slug == "hospital").first()
bank_sector = db.query(Sector).filter(Sector.slug == "bank").first()

# -----------------------------------------------------------------
# 3. ADMIN DASHBOARD SUMMARY METRICS
# -----------------------------------------------------------------
def test_admin_dashboard_metrics():
    summary = get_admin_dashboard_summary(db=db, admin=admin_user)
    actual_orgs = db.query(Organization).count()
    actual_branches = db.query(Branch).count()
    actual_services = db.query(Service).count()
    actual_staff = db.query(Staff).filter(Staff.status == 'ACTIVE').count()
    actual_counters = db.query(Counter).count()
    
    assert summary.total_organizations == actual_orgs, "Org count mismatch"
    assert summary.total_branches == actual_branches, "Branch count mismatch"
    assert summary.total_services == actual_services, "Service count mismatch"
    assert summary.total_staff == actual_staff, "Staff count mismatch"
    assert summary.total_counters == actual_counters, "Counter count mismatch"
    assert len(summary.sectors) == 6, "Sectors breakdown count mismatch"

run_test("Admin Dashboard metrics match exact database table queries", test_admin_dashboard_metrics)

# -----------------------------------------------------------------
# 4. ORGANIZATION MANAGEMENT CRUD
# -----------------------------------------------------------------
test_org_holder = {}

def test_org_crud():
    # Create
    org_in = OrganizationCreate(
        sector_id=hospital_sector.id,
        name=f"Comprehensive Test Hospital {uuid.uuid4().hex[:4]}",
        description="Full multi-specialty care unit",
        city="Coimbatore",
        state="Tamil Nadu",
        address="Avinashi Road",
        phone="0422-1234567",
        email="info@testcare.org",
        status="ACTIVE"
    )
    created = create_organization(req=org_in, db=db, admin=admin_user)
    test_org_holder['org'] = created
    assert created.id is not None
    assert created.name == org_in.name

    # Read by ID
    fetched = get_organization_by_id(org_id=created.id, db=db, admin=admin_user)
    assert fetched.id == created.id

    # Update
    up_in = OrganizationUpdate(name=f"{created.name} (Updated)", city="Coimbatore North")
    updated = update_organization(org_id=created.id, req=up_in, db=db, admin=admin_user)
    assert "Updated" in updated.name
    assert updated.city == "Coimbatore North"

    # Status toggle
    st_in = OrganizationStatusUpdate(status="INACTIVE")
    toggled = update_organization_status(org_id=created.id, req=st_in, db=db, admin=admin_user)
    assert toggled.status == "INACTIVE"

    # Toggle back to ACTIVE
    update_organization_status(org_id=created.id, req=OrganizationStatusUpdate(status="ACTIVE"), db=db, admin=admin_user)

run_test("Organization Management CRUD and status toggles", test_org_crud)

# -----------------------------------------------------------------
# 5. BRANCH MANAGEMENT CRUD & RELATIONSHIP VALIDATION
# -----------------------------------------------------------------
test_branches = {}

def test_branch_crud():
    org = test_org_holder['org']
    # Create Branch A
    b_in_a = BranchCreate(
        organization_id=org.id,
        address="Main Medical Hub A",
        city="Coimbatore",
        state="Tamil Nadu",
        pincode="641014",
        opening_time=time(8, 0),
        closing_time=time(20, 0),
        status="ACTIVE"
    )
    branch_a = create_branch(req=b_in_a, db=db, admin=admin_user)
    test_branches['branch_a'] = branch_a

    # Create Branch B (for isolation tests)
    b_in_b = BranchCreate(
        organization_id=org.id,
        address="Satellite Clinic B",
        city="Pollachi",
        state="Tamil Nadu",
        pincode="642001",
        status="ACTIVE"
    )
    branch_b = create_branch(req=b_in_b, db=db, admin=admin_user)
    test_branches['branch_b'] = branch_b

    # Read by ID
    fetched = get_branch_by_id(branch_id=branch_a.id, db=db, admin=admin_user)
    assert fetched.id == branch_a.id

    # Update
    up_in = BranchUpdate(address="Main Medical Hub A (Renovated)")
    updated = update_branch(branch_id=branch_a.id, req=up_in, db=db, admin=admin_user)
    assert "Renovated" in updated.address

    # Status toggle
    toggled = update_branch_status(branch_id=branch_a.id, req=BranchStatusUpdate(status="INACTIVE"), db=db, admin=admin_user)
    assert toggled.status == "INACTIVE"
    update_branch_status(branch_id=branch_a.id, req=BranchStatusUpdate(status="ACTIVE"), db=db, admin=admin_user)

    # Invalid organization rejection
    try:
        fake_org_id = uuid.uuid4()
        create_branch(req=BranchCreate(organization_id=fake_org_id, address="Invalid", city="C", state="S"), db=db, admin=admin_user)
        assert False, "Allowed branch creation with invalid organization"
    except HTTPException as e:
        assert e.status_code == 400

run_test("Branch Management CRUD, relationship enforcement, and status toggles", test_branch_crud)

# -----------------------------------------------------------------
# 6. SERVICE MANAGEMENT & DURATION VALIDATION
# -----------------------------------------------------------------
def test_service_crud():
    # Valid service
    s_in = ServiceCreate(
        sector_id=hospital_sector.id,
        name=f"Comprehensive Triage {uuid.uuid4().hex[:4]}",
        description="Initial vital signs evaluation",
        average_service_time=12,
        buffer_time=3,
        status="ACTIVE"
    )
    created = create_service(req=s_in, db=db, admin=admin_user)
    assert created.average_service_time == 12
    assert created.buffer_time == 3

    # Read
    fetched = get_service_by_id(service_id=created.id, db=db, admin=admin_user)
    assert fetched.name == created.name

    # Update
    updated = update_service(service_id=created.id, req=ServiceUpdate(average_service_time=15), db=db, admin=admin_user)
    assert updated.average_service_time == 15

    # Toggle status
    toggled = update_service_status(service_id=created.id, req=ServiceStatusUpdate(status="INACTIVE"), db=db, admin=admin_user)
    assert toggled.status == "INACTIVE"
    update_service_status(service_id=created.id, req=ServiceStatusUpdate(status="ACTIVE"), db=db, admin=admin_user)

    # Negative duration validation in schema (Pydantic Field(ge=0))
    from pydantic import ValidationError
    try:
        ServiceCreate(sector_id=hospital_sector.id, name="Invalid Svc", average_service_time=-5)
        assert False, "Allowed negative average_service_time"
    except ValidationError:
        pass # Expected

    try:
        ServiceCreate(sector_id=hospital_sector.id, name="Invalid Svc", average_service_time=10, buffer_time=-2)
        assert False, "Allowed negative buffer_time"
    except ValidationError:
        pass # Expected

run_test("Service Management CRUD and non-negative duration validation", test_service_crud)

# -----------------------------------------------------------------
# 7. COUNTER MANAGEMENT & DATABASE CONSTRAINT
# -----------------------------------------------------------------
def test_counter_management_and_uniqueness():
    branch_a = test_branches['branch_a']
    branch_b = test_branches['branch_b']

    # Create Counter 1 in Branch A
    c1_a = create_counter(
        req=CounterCreate(branch_id=branch_a.id, counter_number=101, name="Desk 101 - Admissions", status="AVAILABLE"),
        db=db,
        admin=admin_user
    )
    assert c1_a.counter_number == 101
    assert c1_a.status == "AVAILABLE"

    # Try duplicate counter 101 in Branch A (must throw 409)
    try:
        create_counter(
            req=CounterCreate(branch_id=branch_a.id, counter_number=101, name="Duplicate Desk", status="AVAILABLE"),
            db=db,
            admin=admin_user
        )
        assert False, "Allowed duplicate counter number in the same branch!"
    except HTTPException as e:
        assert e.status_code == 409

    # Same counter 101 in Branch B (must SUCCEED)
    c1_b = create_counter(
        req=CounterCreate(branch_id=branch_b.id, counter_number=101, name="Branch B Desk 101", status="AVAILABLE"),
        db=db,
        admin=admin_user
    )
    assert c1_b.counter_number == 101

    # Counter status transitions (AVAILABLE, BUSY, CLOSED)
    c1_busy = update_counter_status(counter_id=c1_a.id, req=CounterStatusUpdate(status="BUSY"), db=db, admin=admin_user)
    assert c1_busy.status == "BUSY"
    c1_closed = update_counter_status(counter_id=c1_a.id, req=CounterStatusUpdate(status="CLOSED"), db=db, admin=admin_user)
    assert c1_closed.status == "CLOSED"
    c1_avail = update_counter_status(counter_id=c1_a.id, req=CounterStatusUpdate(status="AVAILABLE"), db=db, admin=admin_user)
    assert c1_avail.status == "AVAILABLE"

run_test("Counter Management, branch-scoped uniqueness (409 on dup), and status transitions", test_counter_management_and_uniqueness)

# -----------------------------------------------------------------
# 8. STAFF MANAGEMENT & ASSIGNMENT TO BRANCH
# -----------------------------------------------------------------
def test_staff_management():
    org = test_org_holder['org']
    branch_a = test_branches['branch_a']
    branch_b = test_branches['branch_b']

    # Assign staff 1 to Branch A
    st1 = assign_staff(
        req=StaffCreate(email=staff_user_1.email, name=staff_user_1.name, organization_id=org.id, branch_id=branch_a.id),
        db=db,
        admin=admin_user
    )
    assert st1.branch_id == branch_a.id

    # Assign staff 2 to Branch B
    st2 = assign_staff(
        req=StaffCreate(email=staff_user_2.email, name=staff_user_2.name, organization_id=org.id, branch_id=branch_b.id),
        db=db,
        admin=admin_user
    )
    assert st2.branch_id == branch_b.id

    # Reassign staff 1 to Branch B
    st1_reassigned = update_staff(staff_id=st1.id, req=StaffUpdate(branch_id=branch_b.id), db=db, admin=admin_user)
    assert st1_reassigned.branch_id == branch_b.id

    # Switch back to Branch A for isolation testing
    update_staff(staff_id=st1.id, req=StaffUpdate(branch_id=branch_a.id), db=db, admin=admin_user)

    # Reject reassignment if branch does not belong to organization
    # Create another org to test mismatch
    other_org = create_organization(
        req=OrganizationCreate(sector_id=bank_sector.id, name=f"Other Bank {uuid.uuid4().hex[:4]}", city="Chennai", state="TN"),
        db=db,
        admin=admin_user
    )
    other_branch = create_branch(
        req=BranchCreate(organization_id=other_org.id, address="Bank St", city="Chennai", state="TN"),
        db=db,
        admin=admin_user
    )
    try:
        # Try to assign staff with mismatched org & branch
        assign_staff(
            req=StaffCreate(email="mismatch@test.com", organization_id=org.id, branch_id=other_branch.id),
            db=db,
            admin=admin_user
        )
        assert False, "Allowed assigning staff with mismatched organization and branch!"
    except HTTPException as e:
        assert e.status_code == 400

run_test("Staff assignment, branch reassignment, and org-branch mismatch prevention", test_staff_management)

# -----------------------------------------------------------------
# 9. BRANCH ISOLATION FOR STAFF DATA ACCESS
# -----------------------------------------------------------------
def test_branch_isolation():
    org = test_org_holder['org']
    branch_a = test_branches['branch_a']
    branch_b = test_branches['branch_b']

    # Get a service
    svc = db.query(Service).filter(Service.sector_id == hospital_sector.id).first()

    today = date.today()

    # Create Appointment & Token in Branch A
    appt_a = Appointment(
        id=uuid.uuid4(),
        user_id=reg_user.id,
        sector_id=hospital_sector.id,
        organization_id=org.id,
        branch_id=branch_a.id,
        service_id=svc.id,
        appointment_date=today,
        appointment_time=time(10, 0),
        status="BOOKED",
        notes="Branch A Patient"
    )
    db.add(appt_a)
    token_a = QueueToken(
        id=uuid.uuid4(),
        appointment_id=appt_a.id,
        token_number="BR-A-001",
        queue_position=1,
        estimated_waiting_time=10,
        status="WAITING"
    )
    db.add(token_a)

    # Create Appointment & Token in Branch B
    appt_b = Appointment(
        id=uuid.uuid4(),
        user_id=reg_user.id,
        sector_id=hospital_sector.id,
        organization_id=org.id,
        branch_id=branch_b.id,
        service_id=svc.id,
        appointment_date=today,
        appointment_time=time(11, 0),
        status="BOOKED",
        notes="Branch B Patient"
    )
    db.add(appt_b)
    token_b = QueueToken(
        id=uuid.uuid4(),
        appointment_id=appt_b.id,
        token_number="BR-B-002",
        queue_position=1,
        estimated_waiting_time=10,
        status="WAITING"
    )
    db.add(token_b)
    db.commit()

    # Query appointments as Staff 1 (Assigned to Branch A)
    staff1_appts = get_staff_appointments(db=db, current_user=staff_user_1)
    staff1_appt_ids = {a.id for a in staff1_appts}
    assert appt_a.id in staff1_appt_ids, "Staff 1 cannot see their own branch appointment!"
    assert appt_b.id not in staff1_appt_ids, "DATA LEAK: Staff 1 saw Branch B appointment!"

    # Query tokens as Staff 1 (Assigned to Branch A)
    staff1_tokens = get_staff_tokens(db=db, current_user=staff_user_1)
    staff1_tok_numbers = {t.token_number for t in staff1_tokens}
    assert "BR-A-001" in staff1_tok_numbers, "Staff 1 cannot see their own branch token!"
    assert "BR-B-002" not in staff1_tok_numbers, "DATA LEAK: Staff 1 saw Branch B queue token!"

    # Query as Staff 2 (Assigned to Branch B)
    staff2_appts = get_staff_appointments(db=db, current_user=staff_user_2)
    staff2_appt_ids = {a.id for a in staff2_appts}
    assert appt_b.id in staff2_appt_ids, "Staff 2 cannot see their own branch appointment!"
    assert appt_a.id not in staff2_appt_ids, "DATA LEAK: Staff 2 saw Branch A appointment!"

    # Staff summary isolation
    summary_1 = get_staff_dashboard_summary(db=db, current_user=staff_user_1)
    assert summary_1.branch_name == branch_a.address

    summary_2 = get_staff_dashboard_summary(db=db, current_user=staff_user_2)
    assert summary_2.branch_name == branch_b.address

run_test("Strict branch data isolation between staff operators", test_branch_isolation)

# -----------------------------------------------------------------
# 10. ROLE-BASED ACCESS CONTROL (ADMIN, STAFF, USER)
# -----------------------------------------------------------------
def test_rbac_security():
    # 1. USER calling ADMIN endpoint -> 403
    try:
        require_admin(reg_user)
        assert False, "Regular USER passed require_admin!"
    except HTTPException as e:
        assert e.status_code == 403

    # 2. STAFF calling ADMIN endpoint -> 403
    try:
        require_admin(staff_user_1)
        assert False, "STAFF passed require_admin!"
    except HTTPException as e:
        assert e.status_code == 403

    # 3. USER calling STAFF endpoint -> 403
    try:
        require_staff(reg_user)
        assert False, "Regular USER passed require_staff!"
    except HTTPException as e:
        assert e.status_code == 403

    # 4. STAFF calling STAFF endpoint -> PASS
    staff_ok = require_staff(staff_user_1)
    assert staff_ok.id == staff_user_1.id

    # 5. ADMIN calling ADMIN endpoint -> PASS
    admin_ok = require_admin(admin_user)
    assert admin_ok.id == admin_user.id

run_test("Role-based authorization enforcements (403 for unauthorized roles)", test_rbac_security)

# -----------------------------------------------------------------
# 11. INVALID ID ERROR HANDLING (HTTP 404)
# -----------------------------------------------------------------
def test_invalid_id_handling():
    random_id = uuid.uuid4()
    
    # Org 404
    try:
        get_organization_by_id(org_id=random_id, db=db, admin=admin_user)
        assert False
    except HTTPException as e:
        assert e.status_code == 404

    # Branch 404
    try:
        get_branch_by_id(branch_id=random_id, db=db, admin=admin_user)
        assert False
    except HTTPException as e:
        assert e.status_code == 404

    # Service 404
    try:
        get_service_by_id(service_id=random_id, db=db, admin=admin_user)
        assert False
    except HTTPException as e:
        assert e.status_code == 404

    # Staff 404
    try:
        get_staff_by_id(staff_id=random_id, db=db, admin=admin_user)
        assert False
    except HTTPException as e:
        assert e.status_code == 404

    # Counter 404
    try:
        get_counter_by_id(counter_id=random_id, db=db, admin=admin_user)
        assert False
    except HTTPException as e:
        assert e.status_code == 404

run_test("Invalid ID handling returns proper HTTP 404 across entities", test_invalid_id_handling)

# -----------------------------------------------------------------
# 12. READ-ONLY APPOINTMENTS AND TOKENS VIEWS
# -----------------------------------------------------------------
def test_read_only_views():
    all_appts = get_all_appointments(db=db, admin=admin_user)
    assert isinstance(all_appts, list)
    if all_appts:
        appt = all_appts[0]
        assert hasattr(appt, 'user_name')
        assert hasattr(appt, 'sector_name')
        assert hasattr(appt, 'organization_name')
        assert hasattr(appt, 'branch_name')
        assert hasattr(appt, 'service_name')
        assert hasattr(appt, 'appointment_date')
        assert hasattr(appt, 'appointment_time')
        assert hasattr(appt, 'status')

    all_tokens = get_all_tokens(db=db, admin=admin_user)
    assert isinstance(all_tokens, list)
    if all_tokens:
        tok = all_tokens[0]
        assert hasattr(tok, 'token_number')
        assert hasattr(tok, 'service_name')
        assert hasattr(tok, 'branch_name')
        assert hasattr(tok, 'status')
        assert hasattr(tok, 'queue_position')

run_test("Admin read-only appointments and tokens queries include all required fields", test_read_only_views)

db.close()

print("\n=========================================================")
print(f"TEST SUMMARY: {len(passed_tests)} Passed, {len(failed_tests)} Failed")
print("=========================================================")

if failed_tests:
    for name, err in failed_tests:
        print(f"FAILED: {name} -> {err}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED SUCCESSFULLY!")
