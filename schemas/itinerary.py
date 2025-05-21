from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CallingPoint(BaseModel):
    locationName: str
    scheduledTime: str

class ItineraryBase(BaseModel):
    service_id: str
    origin: str
    destination: str
    calling_points: List[CallingPoint]
    name: Optional[str]
    tags: Optional[List[str]] = []
    planned_date: Optional[str]

class ItineraryCreate(ItineraryBase):
    user_id: str

class ItineraryResponse(ItineraryBase):
    id: int
    user_id: str
    saved_at: datetime

    class Config:
        orm_mode = True