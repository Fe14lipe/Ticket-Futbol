from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class TicketOut(BaseModel):
    id: int
    order_id: int
    seat_id: int
    ticket_uuid: str
    qr_code_url: Optional[str] = None
    is_validated: bool
    validated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TicketDetailOut(BaseModel):
    ticket_uuid: str
    event_title: str
    event_date: datetime
    event_location: str
    seat_number: str
    qr_code_url: Optional[str] = None
    is_validated: bool
    validated_at: Optional[datetime] = None
    buyer_name: Optional[str] = None

    class Config:
        from_attributes = True
