import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Appointment, Sector, Organization, Branch, Service
from app.core.security import get_current_user
from datetime import date, time
import uuid

client = TestClient(app)

def mock_get_current_user():
    db = SessionLocal()
    user = db.query(User).filter(User.phone == "1234567890").first()
    db.close()
    return user

app.dependency_overrides[get_current_user] = mock_get_current_user

def run_test():
    db = SessionLocal()
    user = db.query(User).filter(User.phone == "1234567890").first()
    sector = db.query(Sector).filter(Sector.slug == "hospital").first()
    org = db.query(Organization).filter(Organization.name == "Test Org").first()
    
    # CREATE A BRAND NEW BRANCH TO AVOID LOCKS
    new_branch = Branch(id=uuid.uuid4(), organization_id=org.id, name="Temp Branch", city="Temp", address="Temp", contact_email="a@a.com", contact_phone="123", status="ACTIVE")
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    
    service = db.query(Service).filter(Service.name == "Test Consultation").first()

    test_date = date(2028, 5, 6)

    # First appointment
    app1 = Appointment(user_id=user.id, sector_id=sector.id, organization_id=org.id, branch_id=new_branch.id, service_id=service.id, appointment_date=test_date, appointment_time=time(9, 0), status="BOOKED", notes="")
    db.add(app1)
    db.commit()
    db.refresh(app1)
    app1_id = str(app1.id)

    # Second appointment on the same date/branch
    app2 = Appointment(user_id=user.id, sector_id=sector.id, organization_id=org.id, branch_id=new_branch.id, service_id=service.id, appointment_date=test_date, appointment_time=time(10, 0), status="BOOKED", notes="")
    db.add(app2)
    db.commit()
    db.refresh(app2)
    app2_id = str(app2.id)
    db.close()

    print("First Token Request:")
    r1 = client.post(f"/api/queue/token/{app1_id}")
    print(r1.status_code)
    print(r1.text)

    print("Second Token Request:")
    r2 = client.post(f"/api/queue/token/{app2_id}")
    print(r2.status_code)
    print(r2.text)

run_test()
