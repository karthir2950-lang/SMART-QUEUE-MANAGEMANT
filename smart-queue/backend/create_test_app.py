import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from app.models.domain import User, Appointment, Sector, Organization, Branch, Service
import uuid
from datetime import date, time

db = SessionLocal()

user = db.query(User).filter(User.phone == "1234567890").first()
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
    appointment_date=date(2028, 2, 2),
    appointment_time=time(10, 0),
    status="BOOKED",
    notes="HTTP Test"
)
db.add(new_app)
db.commit()
db.refresh(new_app)

print(new_app.id)
