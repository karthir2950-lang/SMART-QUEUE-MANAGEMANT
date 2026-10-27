from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import get_db, engine, SessionLocal
from app.models.domain import Sector, Organization, Branch, Service, Counter, User
from app.schemas.domain import SectorResponse, OrganizationResponse, BranchResponse, ServiceResponse, CounterResponse, UserResponse, UserProfileUpdate
from app.core.security import require_user
from app.api.endpoints import appointments

logger = logging.getLogger(__name__)

async def background_reminder_worker():
    """
    Background worker loop that periodically evaluates and processes due appointment reminders (in-app + email).
    Ensures reminder checks occur automatically without requiring client polling.
    """
    from app.services.reminder_service import process_due_reminders
    from app.services.email_reminder_service import process_due_email_reminders
    while True:
        try:
            await asyncio.sleep(30)
            if SessionLocal:
                db = SessionLocal()
                try:
                    process_due_reminders(db)
                    process_due_email_reminders(db)
                finally:
                    db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Background reminder check warning: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: spawn reminder worker
    worker_task = asyncio.create_task(background_reminder_worker())
    yield
    # Shutdown: cancel reminder worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Smart Queue Backend - Step 9", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=settings.BACKEND_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "smart-queue-backend"
    }

@app.get("/api/health/database")
def database_health_check(db: Session = Depends(get_db)):
    if not engine:
        raise HTTPException(status_code=503, detail={"status": "error", "database": "unavailable"})
    
    try:
        # Check connection
        db.execute(text("SELECT 1"))
        
        # Check tables count
        tables_query = text("""
            SELECT count(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables_count = db.execute(tables_query).scalar()
        
        # Get counts for setup page
        sectors_count = db.query(Sector).count()
        organizations_count = db.query(Organization).count()
        branches_count = db.query(Branch).count()
        services_count = db.query(Service).count()
        
        return {
            "status": "ok", 
            "database": "connected",
            "stats": {
                "tables_count": tables_count,
                "sectors": sectors_count,
                "organizations": organizations_count,
                "branches": branches_count,
                "services": services_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail={"status": "error", "database": "unavailable", "message": str(e)})

# =======================
# MASTER DATA API Endpoints
# =======================

@app.get("/api/sectors", response_model=List[SectorResponse])
def get_sectors(db: Session = Depends(get_db)):
    return db.query(Sector).filter(Sector.status == 'ACTIVE').order_by(Sector.name).all()

@app.get("/api/sectors/{sector_id_or_slug}", response_model=SectorResponse)
def get_sector(sector_id_or_slug: str, db: Session = Depends(get_db)):
    try:
        val_uuid = UUID(sector_id_or_slug)
        sector = db.query(Sector).filter(Sector.id == val_uuid).first()
    except (ValueError, AttributeError):
        sector = db.query(Sector).filter(Sector.slug == sector_id_or_slug).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found")
    return sector

@app.get("/api/organizations", response_model=List[OrganizationResponse])
def get_organizations(sector_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Organization).filter(Organization.status == 'ACTIVE')
    if sector_id:
        query = query.filter(Organization.sector_id == sector_id)
    return query.order_by(Organization.name).all()

@app.get("/api/organizations/{org_id}", response_model=OrganizationResponse)
def get_organization(org_id: UUID, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@app.get("/api/branches", response_model=List[BranchResponse])
def get_branches(organization_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Branch).filter(Branch.status == 'ACTIVE')
    if organization_id:
        query = query.filter(Branch.organization_id == organization_id)
    return query.order_by(Branch.city, Branch.address).all()

@app.get("/api/branches/{branch_id}", response_model=BranchResponse)
def get_branch(branch_id: UUID, db: Session = Depends(get_db)):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch

@app.get("/api/services", response_model=List[ServiceResponse])
def get_services(sector_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Service).filter(Service.status == 'ACTIVE')
    if sector_id:
        query = query.filter(Service.sector_id == sector_id)
    return query.order_by(Service.name).all()

@app.get("/api/services/{service_id}", response_model=ServiceResponse)
def get_service(service_id: UUID, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@app.get("/api/counters", response_model=List[CounterResponse])
def get_counters(branch_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Counter)
    if branch_id:
        query = query.filter(Counter.branch_id == branch_id)
    return query.all()

@app.get("/api/counters/{counter_id}", response_model=CounterResponse)
def get_counter(counter_id: UUID, db: Session = Depends(get_db)):
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if not counter:
        raise HTTPException(status_code=404, detail="Counter not found")
    return counter

# =======================
# AUTH API Endpoints
# =======================

from pydantic import BaseModel
import jwt
import time

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None

class SignupRequest(BaseModel):
    email: str
    name: str
    password: Optional[str] = None
    phone: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

@app.post("/api/auth/login", response_model=LoginResponse)
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    clean_email = login_req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user:
        # Default new users to USER role. Never grant ADMIN or STAFF privileges automatically.
        role = "USER"
        user_name = clean_email.split('@')[0].replace('.', ' ').title()
            
        user = User(
            id=uuid.uuid4(),
            name=user_name,
            email=clean_email,
            phone=f"usr-{uuid.uuid4().hex[:8]}",
            role=role,
            status="ACTIVE"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
            
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": int(time.time() + 86400 * 7),
        "user_metadata": {
            "full_name": user.name,
            "role": user.role
        }
    }
    token = jwt.encode(payload, "secret-test-key", algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/api/auth/signup", response_model=LoginResponse)
def signup(signup_req: SignupRequest, db: Session = Depends(get_db)):
    clean_email = signup_req.email.strip().lower()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account with this email already exists. Please login instead.")
        
    # Public signups always receive USER role
    role = "USER"
    new_user = User(
        id=uuid.uuid4(),
        name=signup_req.name.strip() or clean_email.split('@')[0].title(),
        email=clean_email,
        phone=signup_req.phone or f"usr-{uuid.uuid4().hex[:8]}",
        role=role,
        status="ACTIVE"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    payload = {
        "sub": str(new_user.id),
        "email": new_user.email,
        "exp": int(time.time() + 86400 * 7),
        "user_metadata": {
            "full_name": new_user.name,
            "role": new_user.role
        }
    }
    token = jwt.encode(payload, "secret-test-key", algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }

@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(user: User = Depends(require_user)):
    return user

@app.put("/api/auth/profile", response_model=UserResponse)
def update_current_user_profile(
    profile_update: UserProfileUpdate, 
    user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    if profile_update.name is not None:
        user.name = profile_update.name
    if profile_update.email is not None:
        user.email = profile_update.email
    db.commit()
    db.refresh(user)
    return user

# =======================
# APPOINTMENTS API Endpoints
# =======================
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])

# =======================
# QUEUE API Endpoints
# =======================
from app.api.endpoints import queue
app.include_router(queue.router, prefix="/api/queue", tags=["queue"])

# =======================
# ADMIN API Endpoints
# =======================
from app.api.endpoints import admin
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# =======================
# STAFF API Endpoints
# =======================
from app.api.endpoints import staff
app.include_router(staff.router, prefix="/api/staff", tags=["staff"])

# =======================
# NOTIFICATIONS API (STEP 9)
# =======================
from app.api.endpoints import notifications
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

# =======================
# REAL-TIME STREAM (STEP 9)
# =======================
from app.api.endpoints import stream
app.include_router(stream.router, prefix="/api/stream", tags=["stream"])
