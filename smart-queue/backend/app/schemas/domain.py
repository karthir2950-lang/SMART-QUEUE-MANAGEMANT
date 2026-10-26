from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime, time

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseSchema):
    name: Optional[str] = None
    email: Optional[str] = None

class UserResponse(BaseSchema):
    id: UUID
    name: str
    email: Optional[str] = None
    role: str
    status: str
    customer_profile_id: Optional[UUID] = None
    can_access_user_portal: Optional[bool] = True

class SectorBase(BaseSchema):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    status: Optional[str] = "ACTIVE"

class SectorResponse(SectorBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class OrganizationBase(BaseSchema):
    id: UUID
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

class OrganizationResponse(OrganizationBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class BranchBase(BaseSchema):
    id: UUID
    organization_id: UUID
    address: str
    city: str
    state: str
    pincode: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    status: Optional[str] = "ACTIVE"

class BranchResponse(BranchBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ServiceBase(BaseSchema):
    id: UUID
    sector_id: UUID
    name: str
    description: Optional[str] = None
    average_service_time: int
    buffer_time: Optional[int] = 0
    status: Optional[str] = "ACTIVE"

class ServiceResponse(ServiceBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CounterBase(BaseSchema):
    id: UUID
    branch_id: UUID
    name: str
    counter_number: int
    status: Optional[str] = "CLOSED"
    current_token_id: Optional[UUID] = None

class CounterResponse(CounterBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
