import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Appointment, Sector, Organization, Branch, Service
from app.core.security import get_current_user
import uuid
from datetime import date, time

client = TestClient(app)
db = SessionLocal()

user = db.query(User).filter(User.phone == "1234567890").first()
app.dependency_overrides[get_current_user] = lambda: user

sector = db.query(Sector).filter(Sector.slug == "hospital").first()
org = db.query(Organization).filter(Organization.name == "Test Org").first()
branch = db.query(Branch).filter(Branch.city == "Test City").first()
service = db.query(Service).filter(Service.name == "Test Consultation").first()

new_app = Appointment(
    user_id=user.id,
    sector_id=sector.id,
    organization_id=org.id,
    branch_id=branch.id,
    service_id=service.id,
    appointment_date=date(2028, 1, 1),
    appointment_time=time(9, 0),
    status="BOOKED",
    notes="Test API debug"
)
db.add(new_app)
db.commit()
db.refresh(new_app)

print(f"Testing with NEW Appointment ID: {new_app.id}")
response = client.post(f"/api/queue/token/{new_app.id}")
print(f"Status: {response.status_code}")
print(f"Body: {response.json()}")

