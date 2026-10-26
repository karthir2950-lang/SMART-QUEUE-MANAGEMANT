import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("queue_events columns:")
    result = db.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'queue_events';"))
    for row in result:
        print(row)
finally:
    db.close()
