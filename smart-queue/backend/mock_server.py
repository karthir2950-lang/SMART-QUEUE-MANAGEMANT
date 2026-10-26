import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import appointments, queue
from app.db.database import Base, engine, SessionLocal
from app.core.security import get_current_user
from app.models.domain import User

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Queue API (Mock Auth)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock get_current_user
def mock_get_current_user():
    db = SessionLocal()
    user = db.query(User).filter(User.phone == "1234567890").first()
    db.close()
    return user

app.dependency_overrides[get_current_user] = mock_get_current_user

app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(queue.router, prefix="/api/queue", tags=["queue"])

import uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005)
