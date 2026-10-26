from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime, time
from uuid import UUID

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class SectorStat(BaseModel):
    id: UUID
    name: str
    slug: str
    total_organizations: int
    total_branches: int
    total_services: int

class AdminDashboardSummary(BaseModel):
    total_organizations: int
    total_branches: int
    total_services: int
    total_staff: int
    total_counters: int
    today_appointments: int
    today_active_tokens: int
    today_completed: int
    sectors: List[SectorStat]

# --- Organization schemas ---
class OrganizationCreate(BaseModel):
    sector_id: UUID
    name: str
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    status: Optional[str] = "ACTIVE"

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    status: Optional[str] = None

class OrganizationStatusUpdate(BaseModel):
    status: str

# --- Branch schemas ---
class BranchCreate(BaseModel):
    organization_id: UUID
    address: str
    city: str
    state: str
    pincode: Optional[str] = None
    phone: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    status: Optional[str] = "ACTIVE"

class BranchUpdate(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    status: Optional[str] = None

class BranchStatusUpdate(BaseModel):
    status: str

# --- Service schemas ---
class ServiceCreate(BaseModel):
    sector_id: UUID
    name: str
    description: Optional[str] = None
    average_service_time: int = Field(ge=0)
    buffer_time: Optional[int] = Field(default=0, ge=0)
    status: Optional[str] = "ACTIVE"

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    average_service_time: Optional[int] = Field(default=None, ge=0)
    buffer_time: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None

class ServiceStatusUpdate(BaseModel):
    status: str

# --- Counter schemas ---
class CounterCreate(BaseModel):
    branch_id: UUID
    counter_number: int = Field(ge=1)
    name: str
    status: Optional[str] = "AVAILABLE"

class CounterUpdate(BaseModel):
    counter_number: Optional[int] = Field(default=None, ge=1)
    name: Optional[str] = None
    status: Optional[str] = None

class CounterStatusUpdate(BaseModel):
    status: str

class CounterAdminResponse(BaseSchema):
    id: UUID
    branch_id: UUID
    branch_name: Optional[str] = None
    name: str
    counter_number: int
    status: str
    current_token_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

# --- Staff schemas ---
class StaffCreate(BaseModel):
    email: str
    organization_id: UUID
    branch_id: UUID
    name: Optional[str] = None

class StaffUpdate(BaseModel):
    organization_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    status: Optional[str] = None

class StaffStatusUpdate(BaseModel):
    status: str

class StaffAdminResponse(BaseSchema):
    id: UUID
    user_id: UUID
    user_name: str
    user_email: Optional[str] = None
    organization_id: UUID
    organization_name: str
    branch_id: UUID
    branch_address: str
    branch_city: str
    role: str
    status: str
    created_at: Optional[datetime] = None

# --- Detailed Appointment / Token responses ---
class AppointmentAdminResponse(BaseSchema):
    id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    sector_name: Optional[str] = None
    organization_name: Optional[str] = None
    branch_name: Optional[str] = None
    service_name: Optional[str] = None
    appointment_date: date
    appointment_time: time
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class TokenAdminResponse(BaseSchema):
    id: UUID
    appointment_id: UUID
    token_number: str
    service_name: Optional[str] = None
    branch_name: Optional[str] = None
    appointment_date: Optional[date] = None
    status: str
    queue_position: Optional[int] = None
    estimated_waiting_time: Optional[int] = None
    created_at: Optional[datetime] = None

# --- Staff portal schemas ---
class StaffDashboardSummary(BaseModel):
    staff_name: str
    staff_email: Optional[str] = None
    organization_name: str
    branch_name: str
    branch_city: str
    assigned_counter: Optional[str] = None
    today_appointments: int
    waiting_tokens: int
    completed_today: int
