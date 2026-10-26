import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Appointment, Sector, Organization, Branch, Service
from app.core.security import get_current_user
from datetime import date, time

client = TestClient(app)
db = SessionLocal()

user = db.query(User).filter(User.phone == "1234567890").first()
app.dependency_overrides[get_current_user] = lambda: user

sector = db.query(Sector).filter(Sector.slug == "hospital").first()
org = db.query(Organization).filter(Organization.name == "Test Org").first()
branch = db.query(Branch).filter(Branch.city == "Test City").first()
service = db.query(Service).filter(Service.name == "Test Consultation").first()

test_date = date(2028, 3, 3)

# First appointment
app1 = Appointment(user_id=user.id, sector_id=sector.id, organization_id=org.id, branch_id=branch.id, service_id=service.id, appointment_date=test_date, appointment_time=time(9, 0), status="BOOKED", notes="")
db.add(app1)
db.commit()
db.refresh(app1)

print("First Token Request:")
r1 = client.post(f"/api/queue/token/{app1.id}")
print(r1.status_code)
if r1.status_code != 200: print(r1.json())

# Second appointment on the same date/branch
app2 = Appointment(user_id=user.id, sector_id=sector.id, organization_id=org.id, branch_id=branch.id, service_id=service.id, appointment_date=test_date, appointment_time=time(10, 0), status="BOOKED", notes="")
db.add(app2)
db.commit()
db.refresh(app2)

print("Second Token Request:")
r2 = client.post(f"/api/queue/token/{app2.id}")
print(r2.status_code)
if r2.status_code != 200: print(r2.json())
