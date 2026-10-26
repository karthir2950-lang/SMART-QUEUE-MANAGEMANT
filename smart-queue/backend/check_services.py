import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("Services schema:")
    result = db.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'services';"))
    for row in result:
        print(row)
        
    print("\nSome services:")
    result = db.execute(text("SELECT id, name, average_service_time, buffer_time FROM services LIMIT 5;"))
    for row in result:
        print(row)
finally:
    db.close()
