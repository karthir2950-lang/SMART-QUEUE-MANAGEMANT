import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("""
        UPDATE auth.users 
        SET encrypted_password = crypt('Admin@123456', gen_salt('bf')),
            raw_app_meta_data = jsonb_set(
                COALESCE(raw_app_meta_data, '{}'::jsonb),
                '{providers}',
                '["google", "email"]'::jsonb
            )
        WHERE email IN ('madheshr406@gmail.com', 'karthir2950@gmail.com');
    """))
    db.commit()
    print("Successfully set password for madheshr406@gmail.com and karthir2950@gmail.com via pgcrypto!")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
