import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Sector, Organization, Branch, Service
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

def test_create_appointment():
    db = SessionLocal()
    sector = db.query(Sector).filter(Sector.slug == "hospital").first()
    org = db.query(Organization).filter(Organization.name == "Test Org").first()
    branch = db.query(Branch).filter(Branch.city == "Test City").first()
    service = db.query(Service).filter(Service.name == "Test Consultation").first()
    
    # Clean up existing appointment to avoid 409 conflict
    from app.models.domain import Appointment
    user = mock_get_current_user()
    existing = db.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.appointment_date == "2030-01-01",
        Appointment.appointment_time == "12:00:00"
    ).first()
    if existing:
        db.delete(existing)
        db.commit()

    payload = {
        "sector_id": str(sector.id),
        "organization_id": str(org.id),
        "branch_id": str(branch.id),
        "service_id": str(service.id),
        "appointment_date": "2030-01-01",
        "appointment_time": "12:00:00",
        "notes": "Test"
    }
    
    db.close()

    r = client.post("/api/appointments", json=payload)
    print(r.status_code)
    print(r.text)

test_create_appointment()
