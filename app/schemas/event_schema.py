from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class SeatOut(BaseModel):
    id: int
    event_id: int
    seat_number: str
    status: str

    class Config:
        from_attributes = True

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    date: datetime
    location: str
    ticket_price: float
    total_seats: int
    is_visible: Optional[bool] = True

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    ticket_price: Optional[float] = None
    is_visible: Optional[bool] = None

class EventOut(EventBase):
    id: int

    class Config:
        from_attributes = True

class EventDetailOut(EventOut):
    seats: List[SeatOut] = []

    class Config:
        from_attributes = True
