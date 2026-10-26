import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("Constraints for queue_events:")
    result = db.execute(text("""
        SELECT conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'queue_events';
    """))
    for row in result:
        print(row)
finally:
    db.close()
