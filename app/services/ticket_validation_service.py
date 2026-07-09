import logging
from sqlalchemy.orm import Session
from app.models.ticket import Ticket
from app.models.seat import Seat
from app.models.event import Event
from app.models.user import User
from app.models.order import Order
from datetime import datetime

logger = logging.getLogger(__name__)

class TicketValidationService:
    def validate_ticket_by_uuid(self, db: Session, ticket_uuid: str) -> dict:
        """
        Validates a ticket scan. If the ticket exists and hasn't been scanned, marks it as used.
        """
        ticket = db.query(Ticket).filter(Ticket.ticket_uuid == ticket_uuid).first()
        if not ticket:
            return {
                "success": False,
                "status": "NOT_FOUND",
                "message": "Ticket does not exist in the database."
            }

        # Check if the ticket is already scanned
        if ticket.is_validated:
            # Fetch event details for display in response
            seat = db.query(Seat).filter(Seat.id == ticket.seat_id).first()
            event = db.query(Event).filter(Event.id == seat.event_id).first() if seat else None
            event_title = event.title if event else "Unknown Match"
            seat_number = seat.seat_number if seat else "N/A"
            
            logger.warning(f"Double entry warning! Ticket {ticket_uuid} was already scanned at {ticket.validated_at}")
            return {
                "success": False,
                "status": "ALREADY_USED",
                "message": f"CRITICAL: Ticket has already been validated on {ticket.validated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                "event_title": event_title,
                "seat_number": seat_number,
                "validated_at": ticket.validated_at
            }

        # Mark ticket as validated (used)
        ticket.is_validated = True
        ticket.validated_at = datetime.utcnow()
        db.commit()

        # Fetch details for the validator screen
        seat = db.query(Seat).filter(Seat.id == ticket.seat_id).first()
        event = db.query(Event).filter(Event.id == seat.event_id).first() if seat else None
        order = db.query(Order).filter(Order.id == ticket.order_id).first() if ticket else None
        buyer = db.query(User).filter(User.id == order.user_id).first() if order else None
        
        event_title = event.title if event else "Unknown Match"
        seat_number = seat.seat_number if seat else "N/A"
        buyer_name = buyer.full_name if buyer else "Valued Client"

        logger.info(f"Ticket {ticket_uuid} successfully validated at {ticket.validated_at}")
        return {
            "success": True,
            "status": "SUCCESS",
            "message": "Ticket validated successfully! Access GRANTED.",
            "event_title": event_title,
            "seat_number": seat_number,
            "buyer_name": buyer_name,
            "validated_at": ticket.validated_at
        }

    def get_ticket_details(self, db: Session, ticket_uuid: str) -> dict:
        """
        Retrieves ticket details for public display page (Jinja2 view).
        """
        ticket = db.query(Ticket).filter(Ticket.ticket_uuid == ticket_uuid).first()
        if not ticket:
            return None
        
        seat = db.query(Seat).filter(Seat.id == ticket.seat_id).first()
        event = db.query(Event).filter(Event.id == seat.event_id).first() if seat else None
        order = db.query(Order).filter(Order.id == ticket.order_id).first()
        buyer = db.query(User).filter(User.id == order.user_id).first()
        
        return {
            "ticket_uuid": ticket.ticket_uuid,
            "event_title": event.title if event else "Unknown Event",
            "event_date": event.date if event else None,
            "event_location": event.location if event else "Unknown Location",
            "seat_number": seat.seat_number if seat else "N/A",
            "qr_code_url": ticket.qr_code_url,
            "is_validated": ticket.is_validated,
            "validated_at": ticket.validated_at,
            "buyer_name": buyer.full_name if buyer else "Client"
        }

ticket_validation_service = TicketValidationService()
