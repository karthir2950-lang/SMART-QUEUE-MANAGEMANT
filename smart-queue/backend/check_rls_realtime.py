import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import engine, text

with engine.connect() as conn:
    print('--- TABLES WITH RLS ---')
    r = conn.execute(text("""
        SELECT relname, relrowsecurity 
        FROM pg_class 
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace 
        WHERE pg_namespace.nspname = 'public' AND relkind = 'r'
        ORDER BY relname;
    """))
    for row in r:
        print(f"Table: {row[0]}, RLS enabled: {row[1]}")
    
    print('\n--- EXISTING POLICIES ---')
    p = conn.execute(text("""
        SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check 
        FROM pg_policies 
        WHERE schemaname = 'public';
    """))
    policies = p.fetchall()
    if not policies:
        print("No RLS policies defined in public schema.")
    else:
        for row in policies:
            print(row)
            
    print('\n--- REALTIME PUBLICATION TABLES ---')
    try:
        pub = conn.execute(text("""
            SELECT tablename 
            FROM pg_publication_tables 
            WHERE pubname = 'supabase_realtime';
        """))
        pubs = pub.fetchall()
        if not pubs:
            print("No tables in supabase_realtime publication.")
        else:
            for row in pubs:
                print(f"Publication supabase_realtime includes: {row[0]}")
    except Exception as e:
        print(f"Error checking publications: {e}")
