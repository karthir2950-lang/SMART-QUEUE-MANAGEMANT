from pydantic import BaseModel, UUID4, validator
from typing import List, Optional
from datetime import date, time, datetime

class AppointmentCreate(BaseModel):
    sector_id: UUID4
    organization_id: UUID4
    branch_id: UUID4
    service_id: UUID4
    appointment_date: date
    appointment_time: time
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: UUID4
    user_id: Optional[UUID4] = None
    sector_id: Optional[UUID4] = None
    organization_id: Optional[UUID4] = None
    branch_id: Optional[UUID4] = None
    service_id: Optional[UUID4] = None
    appointment_date: date
    appointment_time: time
    status: str
    notes: Optional[str] = None
    created_at: datetime
    
    # Human-readable names for frontend convenience
    sector_name: Optional[str] = None
    organization_name: Optional[str] = None
    branch_name: Optional[str] = None
    service_name: Optional[str] = None

    # Token and queue details
    token_number: Optional[str] = None
    queue_token_id: Optional[UUID4] = None
    queue_position: Optional[int] = None
    estimated_waiting_time: Optional[int] = None
    qr_secure_token: Optional[str] = None

    class Config:
        from_attributes = True

class AvailableSlotRequest(BaseModel):
    branch_id: UUID4
    service_id: UUID4
    appointment_date: date

class AvailableSlot(BaseModel):
    time: time
    available: bool