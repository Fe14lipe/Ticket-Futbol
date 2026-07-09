from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from app.db.database import Base
from sqlalchemy.orm import relationship

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    date = Column(DateTime, nullable=False)
    location = Column(String, nullable=False)
    ticket_price = Column(Float, nullable=False)
    total_seats = Column(Integer, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)

    seats = relationship("Seat", back_populates="event", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="event", cascade="all, delete-orphan")
