from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class NotificationResponse(BaseSchema):
    id: UUID
    user_id: UUID
    appointment_id: Optional[UUID] = None
    type: str
    title: str
    message: str
    is_read: bool
    sent_at: Optional[datetime] = None
    created_at: datetime

class NotificationListResponse(BaseSchema):
    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int

class AIPredictionResponse(BaseSchema):
    token_id: Optional[UUID] = None
    token_number: Optional[str] = None
    people_ahead: int
    active_counters_count: int
    base_service_minutes: int
    dynamic_avg_handling_minutes: float
    predicted_wait_minutes: int
    min_wait_minutes: int
    max_wait_minutes: int
    confidence_score: int
    congestion_level: str
    turn_probability_next_15m: int
    estimated_call_time: Optional[str] = None
    ai_explanation: str
