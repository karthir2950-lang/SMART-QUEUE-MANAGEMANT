import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("Killing locks...")
    db.execute(text("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND pid <> pg_backend_pid()
          AND state = 'idle in transaction';
    """))
    db.commit()
    print("Locks killed.")
finally:
    db.close()
