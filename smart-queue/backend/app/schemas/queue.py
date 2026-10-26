from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime, date, time

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class QueueTokenResponse(BaseSchema):
    id: UUID
    appointment_id: UUID
    token_number: str
    queue_position: Optional[int] = None
    estimated_waiting_time: Optional[int] = None
    status: str
    counter_id: Optional[UUID] = None
    called_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    # Enrichments
    sector_name: Optional[str] = None
    organization_name: Optional[str] = None
    branch_name: Optional[str] = None
    service_name: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    people_ahead: Optional[int] = None
    qr_secure_token: Optional[str] = None
    currently_serving_token: Optional[str] = None
    currently_serving_counter: Optional[str] = None
    server_time: Optional[datetime] = None

class QueueVerifyResponse(BaseSchema):
    valid: bool
    message: str
    token_number: Optional[str] = None
    sector: Optional[str] = None
    organization: Optional[str] = None
    branch: Optional[str] = None
    service: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    queue_status: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_waiting_time: Optional[int] = None
    people_ahead: Optional[int] = None

class StaffQueueItem(BaseSchema):
    id: UUID
    appointment_id: UUID
    token_number: str
    user_name: Optional[str] = None
    service_name: Optional[str] = None
    queue_position: Optional[int] = None
    status: str
    counter_id: Optional[UUID] = None
    counter_number: Optional[int] = None
    counter_name: Optional[str] = None
    called_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_waiting_time: Optional[int] = None
    appointment_time: Optional[time] = None
    appointment_date: Optional[date] = None
    created_at: Optional[datetime] = None

class StaffCounterInfo(BaseSchema):
    id: UUID
    counter_number: int
    name: str
    status: str
    current_token_id: Optional[UUID] = None

class StaffQueueResponse(BaseSchema):
    organization_name: str
    branch_name: str
    branch_city: str
    assigned_counter: Optional[StaffCounterInfo] = None
    current_token: Optional[StaffQueueItem] = None
    waiting_tokens: list[StaffQueueItem] = []
    waiting_count: int = 0
    today_completed_count: int = 0
    today_serving_count: int = 0
