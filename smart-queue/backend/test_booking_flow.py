import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy.orm import sessionmaker
from app.db.database import SessionLocal
from app.models.domain import User, Sector, Organization, Branch, Service, Appointment
import uuid
from datetime import date, time

def test_full_flow():
    db = SessionLocal()
    try:
        # Get our test data
        user = db.query(User).filter(User.phone == "1234567890").first()
        sector = db.query(Sector).filter(Sector.slug == "hospital").first()
        org = db.query(Organization).filter(Organization.name == "Test Org").first()
        branch = db.query(Branch).filter(Branch.city == "Test City").first()
        service = db.query(Service).filter(Service.name == "Test Consultation").first()

        print(f"Using user: {user.id}")

        from app.schemas.appointment import AppointmentCreate
        from app.api.endpoints.appointments import create_appointment
        from app.api.endpoints.queue import create_queue_token

        # 1. Book Appointment
        app_in = AppointmentCreate(
            sector_id=sector.id,
            organization_id=org.id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=date(2027, 10, 6), # Future date to avoid "past" validation
            appointment_time=time(14, 0),
            notes="Test E2E Booking"
        )
        
        print("Booking appointment...")
        try:
            appt_resp = create_appointment(app_in, db, user)
            print(f"Appointment booked successfully! ID: {appt_resp.id}")
        except Exception as e:
            print(f"Failed to book appointment: {e}")
            return

        # 2. Generate Token
        print("Generating Token...")
        try:
            token_resp = create_queue_token(appt_resp.id, db, user)
            print(f"Token generated successfully! Number: {token_resp.token_number}")
            print(token_resp.model_dump_json(indent=2))
        except Exception as e:
            print(f"Failed to generate token: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    test_full_flow()
