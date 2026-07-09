import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_id = Column(Integer, ForeignKey("seats.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Unique ticket UUID (used in the URL: https://tickets.tuapp.com/t/{uuid})
    ticket_uuid = Column(String, default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    
    # Path or URL of the generated QR code
    qr_code_url = Column(String, nullable=True)
    
    # Validation state
    is_validated = Column(Boolean, default=False, nullable=False)
    validated_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="tickets")
    seat = relationship("Seat", back_populates="ticket")
