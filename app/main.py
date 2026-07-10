import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.db.database import engine, Base, SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
# Import base to load all models for metadata creation
from app.db import base
from app.api.routes import admin, events, orders, tickets

from datetime import datetime
from app.models.event import Event
from app.models.seat import Seat

# Configure logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Run migrations at startup
try:
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    
    # Seed default data
    db = SessionLocal()
    try:
        # 1. Seed default admin user if not exists
        admin_exists = db.query(User).filter(User.email == settings.DEFAULT_ADMIN_EMAIL).first()
        if not admin_exists:
            logger.info("Seeding default admin user...")
            hashed_pwd = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
            default_admin = User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=hashed_pwd,
                full_name="Organizador Admin",
                role="admin",
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            logger.info("Default admin user seeded successfully.")
            
        # 2. Seed default World Cup events if not exist
        events_exist = db.query(Event).first()
        if not events_exist:
            logger.info("Seeding default World Cup 2026 matches...")
            world_cup_matches = [
                {
                    "title": "Argentina vs Francia (Gran Final)",
                    "description": "Gran Final de la Copa Mundial FIFA 2026",
                    "date": datetime(2026, 7, 20, 18, 0, 0),
                    "location": "Estadio Metropolitano",
                    "ticket_price": 45.0,
                    "total_seats": 20
                },
                {
                    "title": "Brasil vs Alemania (Semifinal)",
                    "description": "Semifinal de la Copa Mundial FIFA 2026",
                    "date": datetime(2026, 7, 24, 19, 30, 0),
                    "location": "Estadio Metropolitano",
                    "ticket_price": 35.0,
                    "total_seats": 20
                },
                {
                    "title": "España vs Italia (Cuartos)",
                    "description": "Cuartos de Final de la Copa Mundial FIFA 2026",
                    "date": datetime(2026, 7, 28, 17, 0, 0),
                    "location": "Estadio Metropolitano",
                    "ticket_price": 25.0,
                    "total_seats": 20
                }
            ]
            for match in world_cup_matches:
                db_event = Event(
                    title=match["title"],
                    description=match["description"],
                    date=match["date"],
                    location=match["location"],
                    ticket_price=match["ticket_price"],
                    total_seats=match["total_seats"],
                    is_visible=True
                )
                db.add(db_event)
                db.flush()
                
                # Generate seats
                row_letters = ["A", "B"]
                for i in range(20):
                    row_idx = i // 10
                    col_num = (i % 10) + 1
                    row_letter = row_letters[row_idx]
                    seat_number = f"{row_letter}{col_num}"
                    seat = Seat(
                        event_id=db_event.id,
                        seat_number=seat_number,
                        status="AVAILABLE"
                    )
                    db.add(seat)
            db.commit()
            logger.info("Default World Cup 2026 matches seeded successfully.")
    finally:
        db.close()
except Exception as e:
    logger.error(f"Error initializing database: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Plataforma de Boletería Transaccional para Eventos Deportivos - UDLA",
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("static/qrcodes", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API Routers
app.include_router(admin.router, tags=["1. Authentication & Admin Panel"])
app.include_router(events.router, prefix="/events", tags=["2. Events & Seating Maps"])
app.include_router(orders.router, prefix="/orders", tags=["3. Ticket Orders & Checkout"])
app.include_router(tickets.router, tags=["4. Ticket Display & Access Validation"])

@app.get("/")
def redirect_to_portal():
    """
    Redirects root requests to the modern interactive HTML dashboard.
    """
    return RedirectResponse(url="/static/index.html")
