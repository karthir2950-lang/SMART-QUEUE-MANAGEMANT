import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from app.models.domain import User
import uuid

def test():
    db = SessionLocal()
    try:
        # Generate a string UUID
        str_uuid = str(uuid.uuid4())
        
        # Create user
        user = User(id=str_uuid, name="Test", phone=str_uuid[:15], email="test@test.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print("Type after refresh:", type(user.id))
    finally:
        db.close()

test()
