import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.db.database import SessionLocal
from sqlalchemy import text
from app.models.domain import User, Staff, Branch

db = SessionLocal()
try:
    # 1. Ensure staff@smartqueue.test exists in public.users
    staff_user = db.query(User).filter(User.email == 'staff@smartqueue.test').first()
    if not staff_user:
        import uuid
        staff_user = User(
            id=uuid.uuid4(),
            name="Apollo Staff Member",
            email="staff@smartqueue.test",
            phone="9876543210",
            role="STAFF",
            status="ACTIVE"
        )
        db.add(staff_user)
        db.commit()
        db.refresh(staff_user)

    # 2. Ensure staff record in public.staff assigned to a branch
    staff_record = db.query(Staff).filter(Staff.user_id == staff_user.id).first()
    if not staff_record:
        import uuid
        branch = db.query(Branch).filter(Branch.status == 'ACTIVE').first()
        staff_record = Staff(
            id=uuid.uuid4(),
            user_id=staff_user.id,
            organization_id=branch.organization_id if branch else None,
            branch_id=branch.id if branch else None,
            role="STAFF",
            status="ACTIVE"
        )
        db.add(staff_record)
        db.commit()

    # 3. Add to auth.users and auth.identities so staff can log in with Staff@123456
    db.execute(text("""
        INSERT INTO auth.users (
            id, instance_id, email, encrypted_password, email_confirmed_at,
            raw_app_meta_data, raw_user_meta_data, created_at, updated_at, role, aud
        )
        VALUES (
            :uid,
            '00000000-0000-0000-0000-000000000000',
            'staff@smartqueue.test',
            crypt('Staff@123456', gen_salt('bf')),
            NOW(),
            '{"provider":"email","providers":["email"]}'::jsonb,
            '{"name":"Apollo Staff Member"}'::jsonb,
            NOW(),
            NOW(),
            'authenticated',
            'authenticated'
        )
        ON CONFLICT (id) DO UPDATE 
        SET encrypted_password = crypt('Staff@123456', gen_salt('bf')),
            email_confirmed_at = NOW();
    """), {"uid": staff_user.id})

    db.execute(text("""
        INSERT INTO auth.identities (
            id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
        )
        VALUES (
            uuid_generate_v4(),
            :uid_str,
            :uid,
            json_build_object('sub', :uid_str, 'email', 'staff@smartqueue.test', 'name', 'Apollo Staff Member', 'full_name', 'Apollo Staff Member', 'email_verified', true)::jsonb,
            'email',
            NOW(),
            NOW(),
            NOW()
        )
        ON CONFLICT (provider_id, provider) DO NOTHING;
    """), {"uid": staff_user.id, "uid_str": str(staff_user.id)})

    # 4. Ensure user@smartqueue.test exists in public.users and auth.users
    user_record = db.query(User).filter(User.email == 'user@smartqueue.test').first()
    if not user_record:
        import uuid
        user_record = User(
            id=uuid.uuid4(),
            name="Regular Citizen",
            email="user@smartqueue.test",
            phone="9876543211",
            role="USER",
            status="ACTIVE"
        )
        db.add(user_record)
        db.commit()
        db.refresh(user_record)

    db.execute(text("""
        INSERT INTO auth.users (
            id, instance_id, email, encrypted_password, email_confirmed_at,
            raw_app_meta_data, raw_user_meta_data, created_at, updated_at, role, aud
        )
        VALUES (
            :uid,
            '00000000-0000-0000-0000-000000000000',
            'user@smartqueue.test',
            crypt('User@123456', gen_salt('bf')),
            NOW(),
            '{"provider":"email","providers":["email"]}'::jsonb,
            '{"name":"Regular Citizen"}'::jsonb,
            NOW(),
            NOW(),
            'authenticated',
            'authenticated'
        )
        ON CONFLICT (id) DO UPDATE 
        SET encrypted_password = crypt('User@123456', gen_salt('bf')),
            email_confirmed_at = NOW();
    """), {"uid": user_record.id})

    db.execute(text("""
        INSERT INTO auth.identities (
            id, provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at
        )
        VALUES (
            uuid_generate_v4(),
            :uid_str,
            :uid,
            json_build_object('sub', :uid_str, 'email', 'user@smartqueue.test', 'name', 'Regular Citizen', 'full_name', 'Regular Citizen', 'email_verified', true)::jsonb,
            'email',
            NOW(),
            NOW(),
            NOW()
        )
        ON CONFLICT (provider_id, provider) DO NOTHING;
    """), {"uid": user_record.id, "uid_str": str(user_record.id)})

    # Also update admin password to Admin@123456 for madheshr406@gmail.com and karthir2950@gmail.com
    db.execute(text("""
        UPDATE auth.users 
        SET encrypted_password = crypt('Admin@123456', gen_salt('bf')),
            email_confirmed_at = NOW()
        WHERE email IN ('madheshr406@gmail.com', 'karthir2950@gmail.com');
    """))

    db.commit()
    print("SUCCESS: Configured credentials!")
    print("Admin: madheshr406@gmail.com or karthir2950@gmail.com / Admin@123456")
    print("Staff: staff@smartqueue.test / Staff@123456")
    print("User:  user@smartqueue.test / User@123456")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
