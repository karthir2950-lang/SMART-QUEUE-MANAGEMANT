import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Check for duplicate counter numbers in any branch
    dups = db.execute(text("""
        SELECT branch_id, counter_number, COUNT(*)
        FROM counters
        GROUP BY branch_id, counter_number
        HAVING COUNT(*) > 1;
    """)).fetchall()
    print("Existing duplicates in counters:", dups)

    if not dups:
        # Check if constraint exists
        c_check = db.execute(text("""
            SELECT conname FROM pg_constraint WHERE conname = 'uq_branch_counter';
        """)).fetchone()
        if not c_check:
            db.execute(text("""
                ALTER TABLE counters 
                ADD CONSTRAINT uq_branch_counter UNIQUE (branch_id, counter_number);
            """))
            db.commit()
            print("Successfully added uq_branch_counter UNIQUE constraint to counters table!")
        else:
            print("uq_branch_counter UNIQUE constraint already exists!")
    else:
        print("Warning: Duplicates found, cannot add unique constraint without resolving them first.")
except Exception as e:
    db.rollback()
    print("Error:", e)
finally:
    db.close()
