from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.event import Event
from app.models.seat import Seat
from app.schemas.event_schema import EventOut, EventDetailOut, SeatOut

router = APIRouter()

@router.get("/", response_model=List[EventOut])
def get_all_events(db: Session = Depends(get_db)):
    """
    Retrieves all visible matches/events registered in the platform.
    """
    events = db.query(Event).filter(Event.is_visible == True).order_by(Event.date.asc()).all()
    return events

@router.get("/{event_id}", response_model=EventDetailOut)
def get_event_by_id(event_id: int, db: Session = Depends(get_db)):
    """
    Retrieves detailed event description and active seats inventory.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found."
        )
    return event

@router.get("/{event_id}/seats", response_model=List[SeatOut])
def get_event_seats(event_id: int, db: Session = Depends(get_db)):
    """
    Retrieves seat details and real-time locking statuses for a match.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    seats = db.query(Seat).filter(Seat.event_id == event_id).order_by(Seat.seat_number.asc()).all()
    return seats
