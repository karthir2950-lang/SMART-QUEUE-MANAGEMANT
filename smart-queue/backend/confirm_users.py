import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    res = db.execute(text("""
        UPDATE auth.users 
        SET email_confirmed_at = NOW() 
        WHERE email IN ('madheshr406@gmail.com', 'karthir2950@gmail.com')
           OR email_confirmed_at IS NULL;
    """))
    db.commit()
    print(f"Successfully confirmed {res.rowcount} users in auth.users!")
except Exception as e:
    print(f"Error updating auth.users: {e}")
finally:
    db.close()
