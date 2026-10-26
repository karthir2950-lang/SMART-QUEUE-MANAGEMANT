import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class QueueTokenResponse(BaseSchema):
    id: uuid.UUID
    status: str
    sector_name: Optional[str] = None

class QueueToken:
    def __init__(self):
        self.id = uuid.uuid4()
        self.status = "WAITING"

token = QueueToken()
resp = QueueTokenResponse.model_validate(token)
print("Before:", resp.model_dump())
resp.sector_name = "Hospital"
print("After:", resp.model_dump())
