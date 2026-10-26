import uuid
from datetime import date, time
from sqlalchemy.orm import Session
from app.models.domain import Base, User, Sector, Organization, Branch, Service, Counter, Staff

def seed_db(db: Session):
    # Check if sectors exist
    if db.query(Sector).count() > 0:
        return

    # 1. Six standard sectors
    sectors_data = [
        ("Hospital", "hospital", "Healthcare and Hospital sectors"),
        ("Bank", "bank", "Banking and Financial institutions"),
        ("Restaurant", "restaurant", "Food and Dining services"),
        ("Government Office", "government-office", "Public and Government services"),
        ("Retail", "retail", "Retail stores and outlets"),
        ("Supermarket", "supermarket", "Grocery and Supermarkets")
    ]
    sectors = {}
    for name, slug, desc in sectors_data:
        s = Sector(id=uuid.uuid4(), name=name, slug=slug, description=desc, status="ACTIVE")
        db.add(s)
        sectors[slug] = s
    db.flush()

    # 2. Services for sectors
    services_data = {
        "hospital": [("Doctor Consultation", 15), ("Specialist Consultation", 20), ("Laboratory", 10), ("Pharmacy", 5)],
        "bank": [("Cash Counter", 5), ("Account Opening", 25), ("KYC", 10), ("Loan Enquiry", 30)],
        "restaurant": [("Table Booking", 0), ("Dine-in", 45), ("Takeaway", 10), ("Billing", 5)],
        "government-office": [("Certificate Service", 20), ("Document Verification", 15), ("Application Submission", 15)],
        "retail": [("Customer Service", 15), ("Product Assistance", 10), ("Billing Assistance", 5)],
        "supermarket": [("Billing Counter", 5), ("Customer Service", 10), ("Product Return", 10)]
    }
    for slug, s_list in services_data.items():
        sec = sectors[slug]
        for s_name, avg_time in s_list:
            svc = Service(id=uuid.uuid4(), sector_id=sec.id, name=s_name, average_service_time=avg_time, status="ACTIVE")
            db.add(svc)
    db.flush()

    # 3. Organizations and Branches
    orgs_data = [
        ("hospital", "Apollo Hospitals", "Apollo Main Branch", "Greams Road, Thousand Lights", "Chennai", "Tamil Nadu"),
        ("bank", "State Bank of India", "SBI City Center", "123 Anna Salai", "Chennai", "Tamil Nadu"),
        ("restaurant", "Bistro Central", "Bistro Downtown", "45 Cathedral Road", "Chennai", "Tamil Nadu"),
        ("government-office", "Regional Passport Office", "RPO Chennai", "Rayala Towers, Anna Salai", "Chennai", "Tamil Nadu"),
        ("retail", "Lifestyle Fashion", "Lifestyle Express", "Phoenix MarketCity", "Chennai", "Tamil Nadu"),
        ("supermarket", "FreshMart Supermarket", "FreshMart Express", "Velachery Main Road", "Chennai", "Tamil Nadu"),
    ]
    branches = []
    for sec_slug, org_name, branch_name, addr, city, state in orgs_data:
        sec = sectors[sec_slug]
        org = Organization(id=uuid.uuid4(), sector_id=sec.id, name=org_name, city=city, state=state, status="ACTIVE")
        db.add(org)
        db.flush()
        
        br = Branch(id=uuid.uuid4(), organization_id=org.id, address=addr, city=city, state=state, status="ACTIVE")
        db.add(br)
        branches.append((org, br))
    db.flush()

    # 4. Counters for first branch
    first_org, first_br = branches[0]
    c1 = Counter(id=uuid.uuid4(), branch_id=first_br.id, name="General Counter", counter_number=1, status="AVAILABLE")
    c2 = Counter(id=uuid.uuid4(), branch_id=first_br.id, name="Priority Counter", counter_number=2, status="AVAILABLE")
    db.add(c1)
    db.add(c2)
    db.flush()

    # 5. Standard users
    admin_user = User(
        id=uuid.uuid4(),
        name="System Administrator",
        email="admin@smartqueue.test",
        phone="admin-001",
        role="ADMIN",
        status="ACTIVE"
    )
    staff_user = User(
        id=uuid.uuid4(),
        name="Apollo Staff Member",
        email="staff@smartqueue.test",
        phone="staff-001",
        role="STAFF",
        status="ACTIVE"
    )
    reg_user = User(
        id=uuid.uuid4(),
        name="Regular Citizen",
        email="user@smartqueue.test",
        phone="user-001",
        role="USER",
        status="ACTIVE"
    )
    db.add(admin_user)
    db.add(staff_user)
    db.add(reg_user)
    db.flush()

    # 6. Staff assignment
    staff_record = Staff(
        id=uuid.uuid4(),
        user_id=staff_user.id,
        organization_id=first_org.id,
        branch_id=first_br.id,
        role="STAFF",
        status="ACTIVE"
    )
    db.add(staff_record)
    db.commit()
    print("Database successfully seeded with standard sectors, organizations, branches, counters, staff, and test users!")
