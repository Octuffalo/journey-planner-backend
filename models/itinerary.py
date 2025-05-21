from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from models.database import Base

class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    service_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    origin = Column(String)
    destination = Column(String)
    calling_points = Column(JSON)
    planned_date = Column(String, nullable=True)
    tags = Column(JSON, default=[])
    saved_at = Column(DateTime, default=datetime.utcnow)