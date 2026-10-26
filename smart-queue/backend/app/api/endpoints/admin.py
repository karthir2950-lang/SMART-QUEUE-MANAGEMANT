from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, func, and_, or_
from typing import List, Optional
from datetime import date, datetime, timezone
from uuid import UUID

from app.db.database import get_db
from app.core.security import require_admin, get_current_user
from app.models.domain import (
    User, Sector, Organization, Branch, Service, Counter, Staff,
    Appointment, QueueToken, QueueEvent
)
from app.schemas.domain import (
    OrganizationResponse, BranchResponse, ServiceResponse,
    CounterResponse, UserResponse
)
from app.schemas.admin import (
    AdminDashboardSummary, SectorStat,
    OrganizationCreate, OrganizationUpdate, OrganizationStatusUpdate,
    BranchCreate, BranchUpdate, BranchStatusUpdate,
    ServiceCreate, ServiceUpdate, ServiceStatusUpdate,
    CounterCreate, CounterUpdate, CounterStatusUpdate, CounterAdminResponse,
    StaffCreate, StaffUpdate, StaffStatusUpdate, StaffAdminResponse,
    AppointmentAdminResponse, TokenAdminResponse
)

router = APIRouter()

# ========================================================
# 1. ADMIN DASHBOARD SUMMARY
# ========================================================

@router.get("/dashboard/summary", response_model=AdminDashboardSummary)
def get_admin_dashboard_summary(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    today = date.today()

    total_orgs = db.query(Organization).count()
    total_branches = db.query(Branch).count()
    total_services = db.query(Service).count()
    total_staff = db.query(Staff).filter(Staff.status == 'ACTIVE').count()
    total_counters = db.query(Counter).count()

    today_appts = db.query(Appointment).filter(Appointment.appointment_date == today).count()
    today_active_tokens = db.query(QueueToken).join(Appointment).filter(
        Appointment.appointment_date == today,
        QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING'])
    ).count()
    today_completed = db.query(Appointment).filter(
        Appointment.appointment_date == today,
        Appointment.status == 'COMPLETED'
    ).count()

    # Breakdown for all 6 sectors
    sectors = db.query(Sector).order_by(Sector.name).all()
    sector_stats = []
    for s in sectors:
        org_cnt = db.query(Organization).filter(Organization.sector_id == s.id).count()
        branch_cnt = db.query(Branch).join(Organization).filter(Organization.sector_id == s.id).count()
        svc_cnt = db.query(Service).filter(Service.sector_id == s.id).count()
        sector_stats.append(SectorStat(
            id=s.id,
            name=s.name,
            slug=s.slug,
            total_organizations=org_cnt,
            total_branches=branch_cnt,
            total_services=svc_cnt
        ))

    return AdminDashboardSummary(
        total_organizations=total_orgs,
        total_branches=total_branches,
        total_services=total_services,
        total_staff=total_staff,
        total_counters=total_counters,
        today_appointments=today_appts,
        today_active_tokens=today_active_tokens,
        today_completed=today_completed,
        sectors=sector_stats
    )


# ========================================================
# 2. ORGANIZATION MANAGEMENT
# ========================================================

@router.get("/organizations", response_model=List[OrganizationResponse])
def get_organizations(
    sector_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(Organization)
    if sector_id:
        query = query.filter(Organization.sector_id == sector_id)
    if status:
        query = query.filter(Organization.status == status)
    if search:
        query = query.filter(
            or_(
                Organization.name.ilike(f"%{search}%"),
                Organization.city.ilike(f"%{search}%")
            )
        )
    return query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/organizations", response_model=OrganizationResponse)
def create_organization(
    req: OrganizationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    sector = db.query(Sector).filter(Sector.id == req.sector_id).first()
    if not sector:
        raise HTTPException(status_code=400, detail="Invalid sector_id")

    org = Organization(
        sector_id=req.sector_id,
        name=req.name.strip(),
        description=req.description,
        phone=req.phone,
        email=req.email,
        address=req.address,
        city=req.city,
        state=req.state,
        pincode=req.pincode,
        status=req.status or "ACTIVE"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
def get_organization_by_id(
    org_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.put("/organizations/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: UUID,
    req: OrganizationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if req.name is not None:
        org.name = req.name.strip()
    if req.description is not None:
        org.description = req.description
    if req.phone is not None:
        org.phone = req.phone
    if req.email is not None:
        org.email = req.email
    if req.address is not None:
        org.address = req.address
    if req.city is not None:
        org.city = req.city
    if req.state is not None:
        org.state = req.state
    if req.pincode is not None:
        org.pincode = req.pincode
    if req.status is not None:
        org.status = req.status

    db.commit()
    db.refresh(org)
    return org

@router.patch("/organizations/{org_id}/status", response_model=OrganizationResponse)
def update_organization_status(
    org_id: UUID,
    req: OrganizationStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    valid_statuses = ["ACTIVE", "INACTIVE"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status. Must be ACTIVE or INACTIVE")

    org.status = req.status
    db.commit()
    db.refresh(org)
    return org


# ========================================================
# 3. BRANCH MANAGEMENT
# ========================================================

@router.get("/branches", response_model=List[BranchResponse])
def get_branches(
    organization_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(Branch)
    if organization_id:
        query = query.filter(Branch.organization_id == organization_id)
    if status:
        query = query.filter(Branch.status == status)
    if search:
        query = query.filter(
            or_(
                Branch.address.ilike(f"%{search}%"),
                Branch.city.ilike(f"%{search}%")
            )
        )
    return query.order_by(Branch.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/branches", response_model=BranchResponse)
def create_branch(
    req: BranchCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    org = db.query(Organization).filter(Organization.id == req.organization_id).first()
    if not org:
        raise HTTPException(status_code=400, detail="Organization not found")

    branch = Branch(
        organization_id=req.organization_id,
        address=req.address.strip(),
        city=req.city.strip(),
        state=req.state.strip(),
        pincode=req.pincode,
        phone=req.phone,
        opening_time=req.opening_time,
        closing_time=req.closing_time,
        status=req.status or "ACTIVE"
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch

@router.get("/branches/{branch_id}", response_model=BranchResponse)
def get_branch_by_id(
    branch_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch

@router.put("/branches/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: UUID,
    req: BranchUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if req.address is not None:
        branch.address = req.address.strip()
    if req.city is not None:
        branch.city = req.city.strip()
    if req.state is not None:
        branch.state = req.state.strip()
    if req.pincode is not None:
        branch.pincode = req.pincode
    if req.phone is not None:
        branch.phone = req.phone
    if req.opening_time is not None:
        branch.opening_time = req.opening_time
    if req.closing_time is not None:
        branch.closing_time = req.closing_time
    if req.status is not None:
        branch.status = req.status

    db.commit()
    db.refresh(branch)
    return branch

@router.patch("/branches/{branch_id}/status", response_model=BranchResponse)
def update_branch_status(
    branch_id: UUID,
    req: BranchStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    valid_statuses = ["ACTIVE", "INACTIVE"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    branch.status = req.status
    db.commit()
    db.refresh(branch)
    return branch


# ========================================================
# 4. SERVICE MANAGEMENT
# ========================================================

@router.get("/services", response_model=List[ServiceResponse])
def get_services(
    sector_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(Service)
    if sector_id:
        query = query.filter(Service.sector_id == sector_id)
    if status:
        query = query.filter(Service.status == status)
    if search:
        query = query.filter(Service.name.ilike(f"%{search}%"))
    return query.order_by(Service.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/services", response_model=ServiceResponse)
def create_service(
    req: ServiceCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    sector = db.query(Sector).filter(Sector.id == req.sector_id).first()
    if not sector:
        raise HTTPException(status_code=400, detail="Sector not found")

    svc = Service(
        sector_id=req.sector_id,
        name=req.name.strip(),
        description=req.description,
        average_service_time=req.average_service_time,
        buffer_time=req.buffer_time or 0,
        status=req.status or "ACTIVE"
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc

@router.get("/services/{service_id}", response_model=ServiceResponse)
def get_service_by_id(
    service_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    return svc

@router.put("/services/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: UUID,
    req: ServiceUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    if req.name is not None:
        svc.name = req.name.strip()
    if req.description is not None:
        svc.description = req.description
    if req.average_service_time is not None:
        svc.average_service_time = req.average_service_time
    if req.buffer_time is not None:
        svc.buffer_time = req.buffer_time
    if req.status is not None:
        svc.status = req.status

    db.commit()
    db.refresh(svc)
    return svc

@router.patch("/services/{service_id}/status", response_model=ServiceResponse)
def update_service_status(
    service_id: UUID,
    req: ServiceStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")

    valid_statuses = ["ACTIVE", "INACTIVE"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    svc.status = req.status
    db.commit()
    db.refresh(svc)
    return svc


# ========================================================
# 5. STAFF MANAGEMENT
# ========================================================

@router.get("/staff", response_model=List[StaffAdminResponse])
def get_staff_list(
    organization_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(Staff).join(User, Staff.user_id == User.id).join(Organization, Staff.organization_id == Organization.id).join(Branch, Staff.branch_id == Branch.id)

    if organization_id:
        query = query.filter(Staff.organization_id == organization_id)
    if branch_id:
        query = query.filter(Staff.branch_id == branch_id)
    if status:
        query = query.filter(Staff.status == status)
    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    records = query.order_by(Staff.created_at.desc()).all()
    out = []
    for st in records:
        out.append(StaffAdminResponse(
            id=st.id,
            user_id=st.user.id,
            user_name=st.user.name,
            user_email=st.user.email,
            organization_id=st.organization.id,
            organization_name=st.organization.name,
            branch_id=st.branch.id,
            branch_address=st.branch.address,
            branch_city=st.branch.city,
            role=st.role,
            status=st.status,
            created_at=st.created_at
        ))
    return out

@router.post("/staff", response_model=StaffAdminResponse)
def assign_staff(
    req: StaffCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Verify user exists or find by email
    target_user = db.query(User).filter(User.email == req.email.strip()).first()
    if not target_user:
        # Create user profile if missing
        import uuid
        placeholder_phone = f"staff-{uuid.uuid4().hex[:8]}"
        target_user = User(
            id=uuid.uuid4(),
            name=req.name or req.email.split('@')[0],
            email=req.email.strip(),
            phone=placeholder_phone,
            role="STAFF",
            status="ACTIVE"
        )
        db.add(target_user)
        db.commit()
        db.refresh(target_user)
    else:
        # Promote user to STAFF role
        target_user.role = "STAFF"
        db.commit()

    # Verify org and branch
    org = db.query(Organization).filter(Organization.id == req.organization_id).first()
    if not org:
        raise HTTPException(status_code=400, detail="Organization not found")

    branch = db.query(Branch).filter(Branch.id == req.branch_id, Branch.organization_id == req.organization_id).first()
    if not branch:
        raise HTTPException(status_code=400, detail="Branch not found or does not belong to specified Organization")

    # Check if staff record exists for this user
    existing_staff = db.query(Staff).filter(Staff.user_id == target_user.id).first()
    if existing_staff:
        # Update existing assignment
        existing_staff.organization_id = req.organization_id
        existing_staff.branch_id = req.branch_id
        existing_staff.status = "ACTIVE"
        db.commit()
        db.refresh(existing_staff)
        staff_record = existing_staff
    else:
        staff_record = Staff(
            user_id=target_user.id,
            organization_id=req.organization_id,
            branch_id=req.branch_id,
            role="STAFF",
            status="ACTIVE"
        )
        db.add(staff_record)
        db.commit()
        db.refresh(staff_record)

    return StaffAdminResponse(
        id=staff_record.id,
        user_id=target_user.id,
        user_name=target_user.name,
        user_email=target_user.email,
        organization_id=org.id,
        organization_name=org.name,
        branch_id=branch.id,
        branch_address=branch.address,
        branch_city=branch.city,
        role=staff_record.role,
        status=staff_record.status,
        created_at=staff_record.created_at
    )

@router.get("/staff/{staff_id}", response_model=StaffAdminResponse)
def get_staff_by_id(
    staff_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    st = db.query(Staff).filter(Staff.id == staff_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Staff record not found")

    return StaffAdminResponse(
        id=st.id,
        user_id=st.user.id,
        user_name=st.user.name,
        user_email=st.user.email,
        organization_id=st.organization.id,
        organization_name=st.organization.name,
        branch_id=st.branch.id,
        branch_address=st.branch.address,
        branch_city=st.branch.city,
        role=st.role,
        status=st.status,
        created_at=st.created_at
    )

@router.put("/staff/{staff_id}", response_model=StaffAdminResponse)
def update_staff(
    staff_id: UUID,
    req: StaffUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    st = db.query(Staff).filter(Staff.id == staff_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Staff record not found")

    target_org_id = req.organization_id or st.organization_id
    if req.branch_id:
        branch = db.query(Branch).filter(Branch.id == req.branch_id, Branch.organization_id == target_org_id).first()
        if not branch:
            raise HTTPException(status_code=400, detail="Branch does not belong to specified Organization")
        st.branch_id = req.branch_id

    if req.organization_id:
        st.organization_id = req.organization_id
    if req.status:
        st.status = req.status

    db.commit()
    db.refresh(st)

    return StaffAdminResponse(
        id=st.id,
        user_id=st.user.id,
        user_name=st.user.name,
        user_email=st.user.email,
        organization_id=st.organization.id,
        organization_name=st.organization.name,
        branch_id=st.branch.id,
        branch_address=st.branch.address,
        branch_city=st.branch.city,
        role=st.role,
        status=st.status,
        created_at=st.created_at
    )

@router.patch("/staff/{staff_id}/status", response_model=StaffAdminResponse)
def update_staff_status(
    staff_id: UUID,
    req: StaffStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    st = db.query(Staff).filter(Staff.id == staff_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Staff record not found")

    valid_statuses = ["ACTIVE", "INACTIVE"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    st.status = req.status
    db.commit()
    db.refresh(st)

    return StaffAdminResponse(
        id=st.id,
        user_id=st.user.id,
        user_name=st.user.name,
        user_email=st.user.email,
        organization_id=st.organization.id,
        organization_name=st.organization.name,
        branch_id=st.branch.id,
        branch_address=st.branch.address,
        branch_city=st.branch.city,
        role=st.role,
        status=st.status,
        created_at=st.created_at
    )


# ========================================================
# 6. COUNTER MANAGEMENT
# ========================================================

@router.get("/counters", response_model=List[CounterAdminResponse])
def get_counters(
    branch_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(Counter).join(Branch)
    if branch_id:
        query = query.filter(Counter.branch_id == branch_id)
    if status:
        query = query.filter(Counter.status == status)

    counters = query.order_by(Counter.counter_number.asc()).all()
    out = []
    for c in counters:
        out.append(CounterAdminResponse(
            id=c.id,
            branch_id=c.branch_id,
            branch_name=f"{c.branch.address}, {c.branch.city}",
            name=c.name,
            counter_number=c.counter_number,
            status=c.status,
            current_token_id=c.current_token_id,
            created_at=c.created_at
        ))
    return out

@router.post("/counters", response_model=CounterAdminResponse)
def create_counter(
    req: CounterCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    branch = db.query(Branch).filter(Branch.id == req.branch_id).first()
    if not branch:
        raise HTTPException(status_code=400, detail="Branch not found")

    # Uniqueness constraint: Counter number must be unique within a branch
    existing = db.query(Counter).filter(
        Counter.branch_id == req.branch_id,
        Counter.counter_number == req.counter_number
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Counter #{req.counter_number} already exists for this branch")

    counter = Counter(
        branch_id=req.branch_id,
        counter_number=req.counter_number,
        name=req.name.strip(),
        status=req.status or "AVAILABLE"
    )
    db.add(counter)
    db.commit()
    db.refresh(counter)

    return CounterAdminResponse(
        id=counter.id,
        branch_id=counter.branch_id,
        branch_name=f"{branch.address}, {branch.city}",
        name=counter.name,
        counter_number=counter.counter_number,
        status=counter.status,
        current_token_id=counter.current_token_id,
        created_at=counter.created_at
    )

@router.get("/counters/{counter_id}", response_model=CounterAdminResponse)
def get_counter_by_id(
    counter_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    c = db.query(Counter).filter(Counter.id == counter_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Counter not found")

    return CounterAdminResponse(
        id=c.id,
        branch_id=c.branch_id,
        branch_name=f"{c.branch.address}, {c.branch.city}",
        name=c.name,
        counter_number=c.counter_number,
        status=c.status,
        current_token_id=c.current_token_id,
        created_at=c.created_at
    )

@router.put("/counters/{counter_id}", response_model=CounterAdminResponse)
def update_counter(
    counter_id: UUID,
    req: CounterUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    c = db.query(Counter).filter(Counter.id == counter_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Counter not found")

    if req.counter_number is not None and req.counter_number != c.counter_number:
        existing = db.query(Counter).filter(
            Counter.branch_id == c.branch_id,
            Counter.counter_number == req.counter_number
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Counter #{req.counter_number} already exists in this branch")
        c.counter_number = req.counter_number

    if req.name is not None:
        c.name = req.name.strip()
    if req.status is not None:
        valid_statuses = ["AVAILABLE", "BUSY", "CLOSED"]
        if req.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid counter status")
        c.status = req.status

    db.commit()
    db.refresh(c)

    return CounterAdminResponse(
        id=c.id,
        branch_id=c.branch_id,
        branch_name=f"{c.branch.address}, {c.branch.city}",
        name=c.name,
        counter_number=c.counter_number,
        status=c.status,
        current_token_id=c.current_token_id,
        created_at=c.created_at
    )

@router.patch("/counters/{counter_id}/status", response_model=CounterAdminResponse)
def update_counter_status(
    counter_id: UUID,
    req: CounterStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    c = db.query(Counter).filter(Counter.id == counter_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Counter not found")

    valid_statuses = ["AVAILABLE", "BUSY", "CLOSED"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid counter status")

    c.status = req.status
    db.commit()
    db.refresh(c)

    return CounterAdminResponse(
        id=c.id,
        branch_id=c.branch_id,
        branch_name=f"{c.branch.address}, {c.branch.city}",
        name=c.name,
        counter_number=c.counter_number,
        status=c.status,
        current_token_id=c.current_token_id,
        created_at=c.created_at
    )


# ========================================================
# 7. ADMIN APPOINTMENT & TOKEN VIEWS (READ-ONLY IN STEP 7)
# ========================================================

@router.get("/appointments", response_model=List[AppointmentAdminResponse])
def get_all_appointments(
    sector_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    service_id: Optional[UUID] = None,
    target_date: Optional[date] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.user),
            joinedload(Appointment.sector),
            joinedload(Appointment.organization),
            joinedload(Appointment.branch),
            joinedload(Appointment.service),
        )
    )

    if sector_id:
        query = query.filter(Appointment.sector_id == sector_id)
    if organization_id:
        query = query.filter(Appointment.organization_id == organization_id)
    if branch_id:
        query = query.filter(Appointment.branch_id == branch_id)
    if service_id:
        query = query.filter(Appointment.service_id == service_id)
    if target_date:
        query = query.filter(Appointment.appointment_date == target_date)
    if status:
        query = query.filter(Appointment.status == status)

    records = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).offset(skip).limit(limit).all()
    out = []
    for a in records:
        out.append(AppointmentAdminResponse(
            id=a.id,
            user_id=a.user_id,
            user_name=a.user.name if a.user else "User",
            sector_name=a.sector.name if a.sector else "",
            organization_name=a.organization.name if a.organization else "",
            branch_name=f"{a.branch.address}, {a.branch.city}" if a.branch else "",
            service_name=a.service.name if a.service else "",
            appointment_date=a.appointment_date,
            appointment_time=a.appointment_time,
            status=a.status,
            notes=a.notes,
            created_at=a.created_at
        ))
    return out

@router.get("/tokens", response_model=List[TokenAdminResponse])
def get_all_tokens(
    branch_id: Optional[UUID] = None,
    service_id: Optional[UUID] = None,
    target_date: Optional[date] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = (
        db.query(QueueToken)
        .options(
            joinedload(QueueToken.appointment).joinedload(Appointment.service),
            joinedload(QueueToken.appointment).joinedload(Appointment.branch),
        )
    )

    if branch_id:
        query = query.filter(Appointment.branch_id == branch_id)
    if service_id:
        query = query.filter(Appointment.service_id == service_id)
    if target_date:
        query = query.filter(Appointment.appointment_date == target_date)
    if status:
        query = query.filter(QueueToken.status == status)

    tokens = query.order_by(QueueToken.created_at.desc()).offset(skip).limit(limit).all()
    out = []
    for t in tokens:
        out.append(TokenAdminResponse(
            id=t.id,
            appointment_id=t.appointment_id,
            token_number=t.token_number,
            service_name=t.appointment.service.name if t.appointment and t.appointment.service else "",
            branch_name=f"{t.appointment.branch.address}, {t.appointment.branch.city}" if t.appointment and t.appointment.branch else "",
            appointment_date=t.appointment.appointment_date if t.appointment else None,
            status=t.status,
            queue_position=t.queue_position,
            estimated_waiting_time=t.estimated_waiting_time,
            created_at=t.created_at
        ))
    return out
