from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from app.db.database import get_db
from app.models.user import User
from app.models.event import Event
from app.models.seat import Seat
from app.models.ticket import Ticket
from app.models.order import Order
from app.schemas.user_schema import UserCreate, UserOut, Token
from app.schemas.event_schema import EventCreate, EventOut, EventUpdate
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.dependencies import get_current_user, RoleChecker

router = APIRouter()

# Security checkers
admin_only = RoleChecker(["admin"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user (Client, Admin, Staff).
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Authenticates a user and returns a JWT token. (Standard OAuth2 login flow).
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
        "email": user.email
    }

@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: EventCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Admin-only route. Creates an event and automatically populates the stadium seating map.
    """
    # Create Event
    db_event = Event(
        title=event_in.title,
        description=event_in.description,
        date=event_in.date,
        location=event_in.location,
        ticket_price=event_in.ticket_price,
        total_seats=event_in.total_seats
    )
    db.add(db_event)
    db.flush() # flush to get event id

    # Populate seats list in rows (A, B, C...) of 10 seats
    row_letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"]
    
    for i in range(event_in.total_seats):
        row_idx = i // 10
        col_num = (i % 10) + 1
        row_letter = row_letters[row_idx] if row_idx < len(row_letters) else "Z"
        seat_number = f"{row_letter}{col_num}"
        
        seat = Seat(
            event_id=db_event.id,
            seat_number=seat_number,
            status="AVAILABLE"
        )
        db.add(seat)
        
    db.commit()
    db.refresh(db_event)
    return db_event

@router.get("/dashboard", status_code=status.HTTP_200_OK)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Admin-only route. Provides overall platform transactional and inventory health metrics.
    """
    from app.services.ticket_service import ticket_service
    ticket_service.cleanup_expired_locks(db)

    total_events = db.query(Event).count()
    total_tickets = db.query(Ticket).count()
    validated_tickets = db.query(Ticket).filter(Ticket.is_validated == True).count()
    
    total_revenue = db.query(Order).filter(Order.status == "PAID").with_entities(
        Order.total_price
    ).all()
    
    revenue_sum = sum([r[0] for r in total_revenue]) if total_revenue else 0.0
    
    total_seats = db.query(Seat).count()
    booked_seats = db.query(Seat).filter(Seat.status == "BOOKED").count()
    locked_seats = db.query(Seat).filter(Seat.status == "LOCKED").count()
    available_seats = db.query(Seat).filter(Seat.status == "AVAILABLE").count()

    return {
        "summary": {
            "total_events": total_events,
            "total_tickets_sold": total_tickets,
            "validated_tickets": validated_tickets,
            "total_revenue": revenue_sum,
        },
        "inventory": {
            "total_seats": total_seats,
            "booked_seats": booked_seats,
            "locked_seats": locked_seats,
            "available_seats": available_seats
        }
    }

@router.get("/admin/events", response_model=List[EventOut])
def get_admin_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Retrieves all matches/events registered in the platform (Admin-only, including hidden ones).
    """
    return db.query(Event).order_by(Event.date.asc()).all()

@router.put("/admin/events/{event_id}", response_model=EventOut)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Admin-only route. Updates Event details (such as title, date, pricing, or visibility).
    """
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    update_data = event_update.model_dump(exclude_unset=True) if hasattr(event_update, "model_dump") else event_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_event, key, value)
        
    db.commit()
    db.refresh(db_event)
    return db_event

@router.delete("/admin/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Admin-only route. Deletes an event and cascade-deletes all its seats, orders, and tickets.
    """
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    db.delete(db_event)
    db.commit()
    return {"success": True, "message": "Event deleted successfully"}

@router.get("/admin/customers", status_code=status.HTTP_200_OK)
def get_customers_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    """
    Returns a list of all client users, their registration date,
    total orders, and detailed transaction history (orders, tickets, events, seats).
    """
    clients = db.query(User).filter(User.role == "client").all()
    
    result = []
    for client in clients:
        # Get client orders
        orders = db.query(Order).filter(Order.user_id == client.id).order_by(Order.created_at.desc()).all()
        
        # Calculate registration date (first order date or default to current date)
        if orders:
            reg_date = min(o.created_at for o in orders)
        else:
            reg_date = datetime.now() # Fallback
            
        orders_list = []
        for order in orders:
            event = order.event
            tickets = order.tickets
            seats_str = ", ".join([t.seat.seat_number for t in tickets if t.seat])
            
            tickets_detail = []
            for t in tickets:
                tickets_detail.append({
                    "ticket_uuid": t.ticket_uuid,
                    "seat_number": t.seat.seat_number if t.seat else "N/A",
                    "is_validated": t.is_validated,
                    "validated_at": t.validated_at.isoformat() if t.validated_at else None
                })
                
            orders_list.append({
                "order_id": order.id,
                "event_title": event.title if event else "Unknown Event",
                "event_location": event.location if event else "Unknown Location",
                "event_date": event.date.isoformat() if event and event.date else None,
                "status": order.status,
                "total_price": order.total_price,
                "created_at": order.created_at.isoformat(),
                "seats": seats_str,
                "tickets": tickets_detail
            })
            
        result.append({
            "id": client.id,
            "full_name": client.full_name or "Cliente Registrado",
            "email": client.email,
            "created_at": reg_date.isoformat(),
            "total_orders": len(orders),
            "orders": orders_list
        })
        
    return result

