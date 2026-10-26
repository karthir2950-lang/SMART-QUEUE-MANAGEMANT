import os
import sys
import uuid
import datetime
import requests

# Add backend dir to sys.path
sys.path.append(r"c:\SMART QUEUE\smart-queue\backend")

from app.core.config import settings
from supabase import create_client

def run_test():
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    
    # We will just login with a test user if possible, or signup
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    
    print(f"Signing up user {email}...")
    auth_res = supabase.auth.sign_up({"email": email, "password": password})
    if not auth_res.user:
        print("Failed to sign up")
        return
        
    print(f"Logged in as {auth_res.user.email}")
    token = auth_res.session.access_token
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Wait, we need to call health to make sure backend is up
    print("Checking backend health...")
    res = requests.get("http://localhost:8000/api/health")
    print(res.status_code, res.json())
    
    # Get master data to book
    print("Fetching master data...")
    sectors = requests.get("http://localhost:8000/api/sectors").json()
    if not sectors:
        print("No sectors")
        return
    sector = sectors[0]
    
    orgs = requests.get(f"http://localhost:8000/api/organizations?sector_id={sector['id']}").json()
    org = orgs[0]
    
    branches = requests.get(f"http://localhost:8000/api/branches?organization_id={org['id']}").json()
    branch = branches[0]
    
    services = requests.get(f"http://localhost:8000/api/services?sector_id={sector['id']}").json()
    service = services[0]
    
    # Book appointment
    print("Booking appointment...")
    payload = {
        "sector_id": sector['id'],
        "organization_id": org['id'],
        "branch_id": branch['id'],
        "service_id": service['id'],
        "appointment_date": datetime.date.today().isoformat(),
        "appointment_time": "14:00:00",
        "notes": ""
    }
    
    res = requests.post("http://localhost:8000/api/appointments", json=payload, headers=headers)
    print(f"Booking Status: {res.status_code}")
    if res.status_code != 200:
        print(res.text)
        return
        
    appt = res.json()
    print(f"Appointment ID: {appt['id']}")
    
    # Generate token
    print("Generating token...")
    # NOTE: Empty body to mimic frontend
    res = requests.post(f"http://localhost:8000/api/queue/token/{appt['id']}", headers=headers)
    print(f"Token Status: {res.status_code}")
    if res.status_code == 200:
        print(res.json())
    else:
        print(res.text)

if __name__ == "__main__":
    run_test()
