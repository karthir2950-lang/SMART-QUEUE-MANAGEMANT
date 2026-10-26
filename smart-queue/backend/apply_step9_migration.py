import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import engine, text

migration_sql = """
-- 1. Enable RLS on core tables
ALTER TABLE IF EXISTS notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS queue_tokens ENABLE ROW LEVEL SECURITY;

-- 2. Drop existing policies if any to ensure idempotency
DROP POLICY IF EXISTS notifications_user_select ON notifications;
DROP POLICY IF EXISTS notifications_user_update ON notifications;
DROP POLICY IF EXISTS appointments_user_select ON appointments;
DROP POLICY IF EXISTS appointments_user_modify ON appointments;
DROP POLICY IF EXISTS queue_tokens_user_select ON queue_tokens;

-- 3. Create RLS Policies for authenticated users
-- Notifications: users can only view their own notifications; staff/admin can view system notifications
CREATE POLICY notifications_user_select ON notifications
    FOR SELECT TO authenticated
    USING (
        user_id = auth.uid() 
        OR (auth.jwt() ->> 'role') IN ('ADMIN', 'STAFF')
    );

CREATE POLICY notifications_user_update ON notifications
    FOR UPDATE TO authenticated
    USING (
        user_id = auth.uid() 
        OR (auth.jwt() ->> 'role') IN ('ADMIN', 'STAFF')
    )
    WITH CHECK (
        user_id = auth.uid() 
        OR (auth.jwt() ->> 'role') IN ('ADMIN', 'STAFF')
    );

-- Appointments: users can only view their own appointments; staff/admin can view branch appointments
CREATE POLICY appointments_user_select ON appointments
    FOR SELECT TO authenticated
    USING (
        user_id = auth.uid() 
        OR (auth.jwt() ->> 'role') IN ('ADMIN', 'STAFF')
    );

-- Queue Tokens: users can view tokens linked to their appointments; staff/admin can view all tokens
CREATE POLICY queue_tokens_user_select ON queue_tokens
    FOR SELECT TO authenticated
    USING (
        appointment_id IN (SELECT id FROM appointments WHERE user_id = auth.uid())
        OR (auth.jwt() ->> 'role') IN ('ADMIN', 'STAFF')
        OR status = 'WAITING' -- Allows displaying public queue board/position without PII
    );

-- 4. Enable Replica Identity FULL for Realtime change payloads
ALTER TABLE IF EXISTS notifications REPLICA IDENTITY FULL;
ALTER TABLE IF EXISTS appointments REPLICA IDENTITY FULL;
ALTER TABLE IF EXISTS queue_tokens REPLICA IDENTITY FULL;

-- 5. Add tables to supabase_realtime publication
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        CREATE PUBLICATION supabase_realtime;
    END IF;
    
    -- Add notifications
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'notifications'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE notifications;
    END IF;

    -- Add queue_tokens
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'queue_tokens'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE queue_tokens;
    END IF;

    -- Add appointments
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'appointments'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE appointments;
    END IF;
END $$;
"""

def apply_migration():
    print("Applying Step 9 Supabase Realtime & RLS migration to PostgreSQL...")
    with engine.begin() as conn:
        conn.execute(text(migration_sql))
    print("Migration applied successfully!")

if __name__ == "__main__":
    apply_migration()
