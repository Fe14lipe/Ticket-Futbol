from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class OrderCreate(BaseModel):
    event_id: int
    seat_ids: List[int]

class OrderOut(BaseModel):
    id: int
    user_id: int
    event_id: int
    status: str
    total_price: float
    created_at: datetime

    class Config:
        from_attributes = True

class PaymentRequest(BaseModel):
    order_id: int
    card_number: str
    exp_month: int
    exp_year: int
    cvc: str

class PaymentResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    message: str
    tickets: Optional[List[str]] = None
