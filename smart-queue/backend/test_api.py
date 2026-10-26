import os
import sys
import uuid
import datetime

# Add backend dir to sys.path
sys.path.append(r"c:\SMART QUEUE\smart-queue\backend")

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import Appointment, User, Sector, Organization, Branch, Service
from sqlalchemy.orm import Session

# Create a test client
client = TestClient(app)

def run_test():
    db = SessionLocal()
    try:
        # Get a real user or just override dependency
        user = db.query(User).first()
        if not user:
            print("No users found in DB")
            return
            
        print(f"Using user: {user.email} (id: {user.id})")
        
        # Find an appointment for this user or create a fake one just for testing
        appt = db.query(Appointment).filter(Appointment.user_id == user.id, Appointment.status == 'BOOKED').first()
        
        if not appt:
            print("No booked appointment found for user, finding any booked appointment")
            appt = db.query(Appointment).filter(Appointment.status == 'BOOKED').first()
            if not appt:
                print("No booked appointment found in DB. Creating one.")
                sector = db.query(Sector).first()
                org = db.query(Organization).first()
                branch = db.query(Branch).first()
                service = db.query(Service).first()
                
                if not (sector and org and branch and service):
                    print("Missing master data")
                    return
                
                appt = Appointment(
                    user_id=user.id,
                    sector_id=sector.id,
                    organization_id=org.id,
                    branch_id=branch.id,
                    service_id=service.id,
                    appointment_date=datetime.date.today(),
                    appointment_time=datetime.time(10, 0),
                    status="BOOKED"
                )
                db.add(appt)
                db.commit()
                db.refresh(appt)
            else:
                user = db.query(User).filter(User.id == appt.user_id).first()
                
        print(f"Found/Created appointment: {appt.id}")
        
        # Override the dependency to simulate authenticated user
        from app.core.security import get_current_user
        app.dependency_overrides[get_current_user] = lambda: user
        
        print(f"Calling POST /api/queue/token/{appt.id}")
        response = client.post(f"/api/queue/token/{appt.id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
