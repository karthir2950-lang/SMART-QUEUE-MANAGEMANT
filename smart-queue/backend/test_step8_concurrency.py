import os
import sys
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time

sys.path.insert(0, os.path.abspath('.'))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal
from app.models.domain import User, Branch, Counter, Staff, Sector, Service, Appointment, QueueToken, QueueEvent
from app.core.security import get_current_user

db = SessionLocal()

print("=========================================================")
print("RUNNING STEP 8 CONCURRENCY & ATOMICITY TEST SUITE")
print("=========================================================")

staff_user = db.query(User).filter(User.role == 'STAFF').first()
reg_user = db.query(User).filter(User.role == 'USER').first()
staff_record = db.query(Staff).filter(Staff.user_id == staff_user.id, Staff.status == 'ACTIVE').first()
branch_id = staff_record.branch_id
org_id = staff_record.organization_id

# Setup 2 distinct counters for this branch
counter_a = db.query(Counter).filter(Counter.branch_id == branch_id, Counter.counter_number == 1).first()
if not counter_a:
    counter_a = Counter(id=uuid.uuid4(), branch_id=branch_id, name="Desk A", counter_number=1, status="AVAILABLE")
    db.add(counter_a)
else:
    counter_a.status = "AVAILABLE"
    counter_a.current_token_id = None

counter_b = db.query(Counter).filter(Counter.branch_id == branch_id, Counter.counter_number == 2).first()
if not counter_b:
    counter_b = Counter(id=uuid.uuid4(), branch_id=branch_id, name="Desk B", counter_number=2, status="AVAILABLE")
    db.add(counter_b)
else:
    counter_b.status = "AVAILABLE"
    counter_b.current_token_id = None

today = date.today()

# Clear active tokens
active_tokens = (
    db.query(QueueToken)
    .join(Appointment)
    .filter(
        Appointment.branch_id == branch_id,
        Appointment.appointment_date == today,
        QueueToken.status.in_(['WAITING', 'CALLED', 'SERVING'])
    )
    .all()
)
for at in active_tokens:
    at.status = 'SKIPPED'
db.commit()

service = db.query(Service).first()
sector = db.query(Sector).filter(Sector.id == service.sector_id).first()

# Create EXACTLY 1 waiting token
single_appt = Appointment(
    id=uuid.uuid4(),
    user_id=reg_user.id,
    sector_id=sector.id,
    organization_id=org_id,
    branch_id=branch_id,
    service_id=service.id,
    appointment_date=today,
    appointment_time=time(14, 0),
    status="BOOKED",
    notes="Concurrency Test Single Token"
)
db.add(single_appt)
db.commit()

single_token = QueueToken(
    id=uuid.uuid4(),
    appointment_id=single_appt.id,
    token_number="CONCUR-1",
    queue_position=1,
    status="WAITING"
)
db.add(single_token)
db.commit()

staff_user_id = staff_user.id
token_id_str = str(single_token.id)
counter_a_id = str(counter_a.id)
counter_b_id = str(counter_b.id)

# Configure staff auth override with active session query
def get_test_staff():
    s_db = SessionLocal()
    u = s_db.query(User).filter(User.id == staff_user_id).first()
    return u

app.dependency_overrides[get_current_user] = get_test_staff
client = TestClient(app)

# TEST CONCURRENCY:
# Run two concurrent requests calling call-next on two separate counters simultaneously.
# The row-level lock (with_for_update(skip_locked=True)) MUST ensure that exactly ONE
# counter receives the waiting token (200), and the other gets 404 (no waiting tokens).
results = []
barrier = threading.Barrier(2)

def worker(cid):
    barrier.wait()
    r = client.post(f"/api/staff/queue/call-next?counter_id={cid}")
    return (cid, r.status_code, r.text)

with ThreadPoolExecutor(max_workers=2) as executor:
    fut_a = executor.submit(worker, counter_a_id)
    fut_b = executor.submit(worker, counter_b_id)
    results.append(fut_a.result())
    results.append(fut_b.result())

print(f"Concurrent Call Results:")
for cid, status, text in results:
    print(f"Counter {cid[:8]}: Status {status} -> {text[:60]}")

status_codes = [r[1] for r in results]
assert 200 in status_codes, f"Expected exactly one 200, got: {status_codes}"
assert 404 in status_codes, f"Expected other request to receive 404 (no waiting tokens), got: {status_codes}"

successful = [r for r in results if r[1] == 200]
assert len(successful) == 1, f"Expected exactly 1 success, got {len(successful)}"

print("\n[PASS] PostgreSQL row locking (with_for_update + skip_locked) prevented duplicate token assignment!")

# Clean up
db = SessionLocal()
tok = db.query(QueueToken).filter(QueueToken.id == uuid.UUID(token_id_str)).first()
assert tok.status == "CALLED", f"Expected token status CALLED, got {tok.status}"
tok.status = "COMPLETED"
if tok.appointment:
    tok.appointment.status = "COMPLETED"
db.commit()
db.close()

print("ALL CONCURRENCY TESTS PASSED WITH 100% SUCCESS!")
