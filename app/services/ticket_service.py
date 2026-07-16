import logging
from sqlalchemy.orm import Session
from app.models.event import Event
from app.models.seat import Seat
from app.models.order import Order
from app.models.ticket import Ticket
from app.services.seat_lock_service import seat_lock_service
from app.services.payment_processor import payment_processor_service
from fastapi import HTTPException, status
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TicketService:
    def create_order(self, db: Session, user_id: int, event_id: int, seat_ids: list[int]) -> Order:
        """
        Creates a pending ticket purchase order. Uses Redis distributed locks to verify and lock seats.
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # 1. Acquire Redis distributed locks for all seats
        locked_seats = []
        try:
            for seat_id in seat_ids:
                # Check seat exists and belongs to event
                seat = db.query(Seat).filter(Seat.id == seat_id, Seat.event_id == event_id).first()
                if not seat:
                    raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found in this event")
                
                if seat.status == "BOOKED":
                    raise HTTPException(status_code=400, detail=f"Seat {seat.seat_number} is already booked")

                # Acquire distributed lock
                acquired = seat_lock_service.acquire_lock(seat_id, user_id, expire_seconds=300)
                if not acquired:
                    raise HTTPException(
                        status_code=409, 
                        detail=f"Seat {seat.seat_number} is currently being held by another transaction. Please try again."
                    )
                locked_seats.append((seat, seat_id))

            # 2. If all locks succeeded, create the Order and temporarily change status in DB to LOCKED
            total_price = len(seat_ids) * event.ticket_price
            order = Order(
                user_id=user_id,
                event_id=event_id,
                status="PENDING",
                total_price=total_price,
                created_at=datetime.utcnow()
            )
            db.add(order)
            db.flush()  # Get order ID

            for seat, seat_id in locked_seats:
                seat.status = "LOCKED"
                seat.locked_until = datetime.utcnow() # local DB fallback timestamp
            
            db.commit()
            logger.info(f"Order {order.id} created successfully in PENDING state")
            return order

        except HTTPException as e:
            # Rollback locks on failure
            for _, s_id in locked_seats:
                seat_lock_service.release_lock(s_id, user_id)
            raise e
        except Exception as e:
            db.rollback()
            for _, s_id in locked_seats:
                seat_lock_service.release_lock(s_id, user_id)
            logger.error(f"Error creating order: {e}")
            raise HTTPException(status_code=500, detail="Internal server error creating order")

    async def confirm_payment_and_complete_order(self, db: Session, order_id: int, user_id: int, card_info: dict) -> dict:
        """
        Completes payment processing via simulated Lambda and generates tickets + async QR background task.
        """
        order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"Order is already in state: {order.status}")

        # Fetch locked seats for this event (find which ones are LOCKED and will be purchased)
        # In a real app, you would have an OrderItem table. Here, we query seats locked by this order flow
        # For simplicity, we get the list of seats that were locked in Redis or are locked in the DB
        # To identify them cleanly, we will pass the list of seats associated with the purchase
        # Let's query seats for this event that are currently locked
        # Actually, since we don't have an OrderItem table, we'll fetch seats from the database. Let's make sure
        # we know which seats were requested. Let's design the service to fetch seats based on the event and user.
        # Wait, a cleaner approach is that the user passes the seat_ids or we query the ticket/seat locks.
        # Let's write the order to match: we can query the seats for this event that have status = 'LOCKED'.
        # However, to avoid conflicts between different users' locked seats in the DB, let's query seats where status='LOCKED'
        # and we verify they are locked in Redis by this user.
        
        # Query all seats of the event that are in state LOCKED
        locked_db_seats = db.query(Seat).filter(Seat.event_id == order.event_id, Seat.status == "LOCKED").all()
        
        # Filter seats owned in Redis by this user
        user_seats = []
        for s in locked_db_seats:
            lock_key = f"lock:seat:{s.id}"
            if seat_lock_service.client:
                owner = seat_lock_service.client.get(lock_key)
                if owner == str(user_id):
                    user_seats.append(s)
            else:
                # No redis fallback: just take them
                user_seats.append(s)

        if not user_seats:
            # If no seats locked, fail order
            order.status = "CANCELLED"
            db.commit()
            raise HTTPException(status_code=400, detail="No locked seats found for this transaction. Lock might have expired.")

        # 3. Call the Lambda payment endpoint
        payment_result = await payment_processor_service.process_payment(order.id, order.total_price, card_info)
        
        if payment_result.get("success"):
            # Payment Success! Update order and seats
            order.status = "PAID"
            
            created_tickets = []
            for seat in user_seats:
                seat.status = "BOOKED"
                seat.locked_until = None
                
                # Create a Ticket record
                ticket = Ticket(
                    order_id=order.id,
                    seat_id=seat.id,
                    is_validated=False
                )
                db.add(ticket)
                created_tickets.append(ticket)
            
            db.commit() # Commit so ticket records get IDs

            # Import here to avoid circular imports
            from app.tasks.celery_worker import generate_ticket_task
            
            # 4. Trigger asynchronous QR Code generation tasks via Celery worker
            for ticket in created_tickets:
                generate_ticket_task.delay(ticket.id)
                
            # 5. Release Redis locks
            for seat in user_seats:
                seat_lock_service.release_lock(seat.id, user_id)
                
            logger.info(f"Payment confirmed for order {order.id}. Tickets created and queue tasks dispatched.")
            return {
                "success": True,
                "message": "Payment successful, tickets generated",
                "order_id": order.id,
                "tickets": [t.ticket_uuid for t in created_tickets]
            }
        else:
            # Payment Failed! Revert order and seat states
            order.status = "CANCELLED"
            for seat in user_seats:
                seat.status = "AVAILABLE"
                seat.locked_until = None
            db.commit()
            
            # Release Redis locks
            for seat in user_seats:
                seat_lock_service.release_lock(seat.id, user_id)
                
            logger.warning(f"Payment failed for order {order.id}: {payment_result.get('message')}")
            return {
                "success": False,
                "message": payment_result.get("message", "Payment transaction failed"),
                "order_id": order.id
            }

    def cleanup_expired_locks(self, db: Session):
        """
        Cleans up expired seat locks in the database.
        """
        from datetime import datetime, timedelta
        
        # Query seats currently LOCKED
        locked_seats = db.query(Seat).filter(Seat.status == "LOCKED").all()
        if not locked_seats:
            return
            
        db_changed = False
        for seat in locked_seats:
            redis_locked = seat_lock_service.is_locked(seat.id)
            db_expired = False
            if seat.locked_until:
                # 5 minutes TTL fallback
                db_expired = datetime.utcnow() > seat.locked_until + timedelta(minutes=5)
                
            # If it's not locked in Redis and (Redis is active OR the DB fallback time has expired)
            if not redis_locked:
                if seat_lock_service.client is not None or db_expired:
                    seat.status = "AVAILABLE"
                    seat.locked_until = None
                    db_changed = True
                    logger.info(f"Released expired DB lock for seat {seat.id} ({seat.seat_number})")
                    
        if db_changed:
            db.commit()

ticket_service = TicketService()
