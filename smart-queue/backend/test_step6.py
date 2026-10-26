import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import get_db, SessionLocal, engine
from app.models.domain import User, Sector, Organization, Branch, Service, Appointment, QueueToken, QueueEvent, QRToken
import uuid
from datetime import date, time, datetime, timedelta
import requests
import json
import concurrent.futures

BASE_URL = "http://localhost:8000"

def setup_test_data(db):
    # Create User
    user = db.query(User).filter(User.phone == "1234567890").first()
    if not user:
        user = User(id=uuid.uuid4(), name="Test User", phone="1234567890", role="USER")
        db.add(user)
    
    # Create Sector (Hospital)
    sector = db.query(Sector).filter(Sector.slug == "hospital").first()
    if not sector:
        sector = Sector(id=uuid.uuid4(), name="Hospital", slug="hospital")
        db.add(sector)
    
    # Create Organization
    org = db.query(Organization).filter(Organization.name == "Test Org").first()
    if not org:
        org = Organization(id=uuid.uuid4(), sector_id=sector.id, name="Test Org")
        db.add(org)
    
    # Create Branch
    branch = db.query(Branch).filter(Branch.city == "Test City").first()
    if not branch:
        branch = Branch(id=uuid.uuid4(), organization_id=org.id, address="Test Address", city="Test City", state="State")
        db.add(branch)
        
    # Create Service
    service = db.query(Service).filter(Service.name == "Test Consultation").first()
    if not service:
        service = Service(id=uuid.uuid4(), sector_id=sector.id, name="Test Consultation", average_service_time=15)
        db.add(service)
        
    db.commit()
    return user, sector, org, branch, service

def run_tests():
    db = SessionLocal()
    try:
        user, sector, org, branch, service = setup_test_data(db)
        print("Test data setup complete.")
        
        # We can bypass auth for tests by directly calling the create_queue_token logic.
        from app.api.endpoints.queue import create_queue_token, get_queue_token, verify_qr_token
        
        # 1. Create a dummy appointment
        appt = Appointment(
            id=uuid.uuid4(),
            user_id=user.id,
            sector_id=sector.id,
            organization_id=org.id,
            branch_id=branch.id,
            service_id=service.id,
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            status="BOOKED"
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)
        print(f"Created appointment: {appt.id}")
        
        # 2. Call create_queue_token
        # It needs user param to check role/ownership, we can pass our 'user' object
        from fastapi import HTTPException
        try:
            token_resp = create_queue_token(appt.id, db, user)
            print("Token Created successfully!")
            print(token_resp.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error creating token: {e}")
            raise
            
        # 3. Idempotency test
        try:
            token_resp2 = create_queue_token(appt.id, db, user)
            print("Idempotency passed! Second call returned same token.")
            assert token_resp.token_number == token_resp2.token_number
        except Exception as e:
            print(f"Error checking idempotency: {e}")
            raise
            
        # 4. QR Verify test
        try:
            secure_token = token_resp.qr_secure_token
            verify_resp = verify_qr_token(secure_token, db)
            print(f"Verify response: {verify_resp}")
            assert verify_resp.valid == True
        except Exception as e:
            print(f"Error verifying token: {e}")
            raise
            
        # 5. Check queue position calculation
        print(f"Initial Queue Position: {token_resp.queue_position}")
        print(f"People Ahead: {token_resp.people_ahead}")
        print(f"Estimated Wait: {token_resp.estimated_waiting_time}")
            
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
