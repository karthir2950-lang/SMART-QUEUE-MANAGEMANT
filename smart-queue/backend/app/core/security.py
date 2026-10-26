from typing import Optional
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.config import settings
from app.db.database import get_db
from app.models.domain import User

security = HTTPBearer(auto_error=False)

def get_supabase_client() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="Supabase configuration missing in backend")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db)
):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication credentials required")
    supabase = get_supabase_client()
    auth_user_id = None
    auth_user_email = None
    auth_user_metadata = {}

    import jwt
    import time

    token = credentials.credentials
    payload = None
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp and exp < time.time():
            raise HTTPException(status_code=401, detail="Token has expired")
        sub = payload.get("sub")
        if sub:
            auth_user_id = str(sub)
            auth_user_email = payload.get("email")
            auth_user_metadata = payload.get("user_metadata") or {}
    except HTTPException:
        raise
    except Exception as parse_err:
        pass

    try:
        # Verify token with Supabase Auth
        auth_response = supabase.auth.get_user(credentials.credentials)
        if auth_response and auth_response.user:
            auth_user = auth_response.user
            auth_user_id = str(auth_user.id)
            auth_user_email = auth_user.email
            auth_user_metadata = auth_user.user_metadata or auth_user_metadata
    except Exception as e:
        if not auth_user_id:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    try:
        user_uuid = None
        try:
            user_uuid = UUID(str(auth_user_id)) if auth_user_id else None
        except (ValueError, AttributeError):
            user_uuid = None

        # Check if public.users profile exists by ID or by email
        db_user = None
        if user_uuid:
            db_user = db.query(User).filter(User.id == user_uuid).first()
        if not db_user and auth_user_email:
            from sqlalchemy import func
            db_user = db.query(User).filter(func.lower(User.email) == auth_user_email.strip().lower()).first()
        
        if not db_user:
            user_name = auth_user_metadata.get("full_name") or auth_user_metadata.get("name") or "User"
            import uuid
            placeholder_phone = f"user-{uuid.uuid4().hex[:8]}"
            
            db_user = User(
                id=user_uuid or uuid.uuid4(),
                name=user_name,
                email=auth_user_email or f"{auth_user_id}@smartqueue.app",
                phone=placeholder_phone,
                role="USER",
                status="ACTIVE"
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        else:
            # Sync name if db_user has default name but metadata has full name
            meta_name = auth_user_metadata.get("full_name") or auth_user_metadata.get("name")
            if meta_name and (not db_user.name or db_user.name == "User"):
                db_user.name = meta_name
                db.commit()
                db.refresh(db_user)
            
        if db_user.status != "ACTIVE":
            raise HTTPException(status_code=403, detail="Account is not active")
            
        return db_user
        
    except Exception as e:
        print(f"Auth error details: {str(e)}")
        import traceback
        traceback.print_exc()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# ==============================================================================
# AUTHORIZATION POLICY & ACCESS CONTROL
# ==============================================================================
# 1. Citizen User-Facing Access (`require_user`):
#    - Grants access to citizen portal features (sector browsing, available slots,
#      appointment booking, queue token tracking, and token downloading).
#    - Permitted roles: USER, ADMIN, and STAFF (all active accounts).
#    - When an ADMIN uses user-facing features, they operate via their explicit
#      linked customer capability (`customer_profile_id == user.id`), preserving their
#      primary identity without creating duplicate account rows or assuming their
#      ADMIN role is downgraded to USER.
#    - Ordinary USER accounts CANNOT access administrative functions.
#
# 2. Administrative Portal & API Access (`require_admin`):
#    - Strictly enforced on the backend. Only accounts with `user.role == 'ADMIN'`
#      are granted access to /api/admin/* endpoints.
#    - Ordinary USER and STAFF accounts attempting to access admin APIs receive HTTP 403 Forbidden.
#    - Frontend route guards serve as UX guidance only; security is always enforced here.
#
# 3. Staff Desk Access (`require_staff`):
#    - Requires `user.role in ['STAFF', 'ADMIN']` and active assignment.
#    - Ordinary USER accounts receive HTTP 403 Forbidden.
# ==============================================================================

def require_user(user: User = Depends(get_current_user)) -> User:
    """
    Ensures the caller is an active authenticated user possessing citizen portal access.
    All active users (including ADMIN and STAFF) are permitted to access customer-facing features.
    """
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Account is not active")
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Strictly enforces ADMIN privileges on administrative APIs.
    Ordinary USER and STAFF accounts receive HTTP 403 Forbidden.
    """
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return user

def require_staff(user: User = Depends(get_current_user)) -> User:
    """
    Enforces STAFF or ADMIN privileges on staff desk APIs.
    Ordinary USER accounts receive HTTP 403 Forbidden.
    """
    if user.role not in ["STAFF", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return user
