import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("Schema for queue_tokens:")
    result = db.execute(text("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'queue_tokens';"))
    for row in result:
        print(row)
        
    print("\nSchema for queue_events:")
    result = db.execute(text("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'queue_events';"))
    for row in result:
        print(row)
        
    print("\nSchema for qr_tokens:")
    result = db.execute(text("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'qr_tokens';"))
    for row in result:
        print(row)
        
    print("\nForeign keys for queue_tokens:")
    result = db.execute(text("""
    SELECT
        tc.table_name, 
        kcu.column_name, 
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name 
    FROM 
        information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name='queue_tokens';
    """))
    for row in result:
        print(row)

finally:
    db.close()
