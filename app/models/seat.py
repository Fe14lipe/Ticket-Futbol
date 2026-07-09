from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base

class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_number = Column(String, nullable=False)  # e.g., A1, B12
    status = Column(String, default="AVAILABLE", nullable=False)  # AVAILABLE, LOCKED, BOOKED
    locked_until = Column(DateTime, nullable=True)  # Fallback DB TTL lock

    event = relationship("Event", back_populates="seats")
    ticket = relationship("Ticket", back_populates="seat", uselist=False)
