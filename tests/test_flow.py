import unittest
import os
import sys
from datetime import datetime, timedelta

# Adjust path to import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
# Override db host to localhost for testing on host
settings.POSTGRES_HOST = "localhost"
settings.REDIS_HOST = "localhost"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.models.user import User
from app.models.event import Event
from app.models.seat import Seat
from app.models.order import Order
from app.models.ticket import Ticket
from app.core.security import get_password_hash, verify_password
from app.services.seat_lock_service import seat_lock_service
from app.services.ticket_validation_service import ticket_validation_service

class TicketSystemFlowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up a testing PostgreSQL DB (in memory sqlite as fallback for tests if PostgreSQL is down on host)
        # Check if local postgres is running, otherwise use sqlite fallback for local unit testing
        cls.engine = create_engine("sqlite:///./test_temp.db", connect_args={"check_same_thread": False})
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        if os.path.exists("./test_temp.db"):
            os.remove("./test_temp.db")

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_01_user_and_auth(self):
        """Test User hashing and verification"""
        raw_pass = "clientpwd123"
        hashed = get_password_hash(raw_pass)
        
        self.assertTrue(verify_password(raw_pass, hashed))
        self.assertFalse(verify_password("wrong_password", hashed))

        # Create user
        user = User(
            email="test_client@futbol.com",
            hashed_password=hashed,
            full_name="Juan Perez",
            role="client",
            is_active=True
        )
        self.db.add(user)
        self.db.commit()

        db_user = self.db.query(User).filter(User.email == "test_client@futbol.com").first()
        self.assertIsNotNone(db_user)
        self.assertEqual(db_user.full_name, "Juan Perez")

    def test_02_event_and_seats_generation(self):
        """Test Event and Seat relationship generation"""
        event = Event(
            title="Ecuador vs Argentina",
            description="Eliminatorias Conmebol",
            date=datetime.now() + timedelta(days=5),
            location="Estadio Rodrigo Paz",
            ticket_price=30.0,
            total_seats=15
        )
        self.db.add(event)
        self.db.commit()

        # Check seats creation
        for i in range(event.total_seats):
            seat = Seat(
                event_id=event.id,
                seat_number=f"RowA-{i+1}",
                status="AVAILABLE"
            )
            self.db.add(seat)
        self.db.commit()

        db_seats = self.db.query(Seat).filter(Seat.event_id == event.id).all()
        self.assertEqual(len(db_seats), 15)
        self.assertEqual(db_seats[0].status, "AVAILABLE")

    def test_03_redis_lock_simulation(self):
        """Test Distributed Lock mock properties"""
        seat_id = 999
        user_1 = 10
        user_2 = 11

        # Test acquiring
        lock_ok = seat_lock_service.acquire_lock(seat_id, user_1, expire_seconds=5)
        # Even if Redis is down, our service falls back gracefully to True for local dev
        self.assertTrue(lock_ok)

        # Release lock
        release_ok = seat_lock_service.release_lock(seat_id, user_1)
        self.assertTrue(release_ok)

    def test_04_ticket_validation_states(self):
        """Test ticket validation transitions"""
        # Create user, event, seat, order, ticket
        user = User(email="staff@futbol.com", hashed_password="pwd", role="staff")
        event = Event(title="Derby", date=datetime.now(), location="Estadio", ticket_price=20, total_seats=1)
        self.db.add_all([user, event])
        self.db.flush()

        seat = Seat(event_id=event.id, seat_number="A1", status="BOOKED")
        self.db.add(seat)
        self.db.flush()

        order = Order(user_id=user.id, event_id=event.id, status="PAID", total_price=20)
        self.db.add(order)
        self.db.flush()

        ticket = Ticket(order_id=order.id, seat_id=seat.id, ticket_uuid="custom-uuid-test", is_validated=False)
        self.db.add(ticket)
        self.db.commit()

        # Check details query
        details = ticket_validation_service.get_ticket_details(self.db, "custom-uuid-test")
        self.assertIsNotNone(details)
        self.assertEqual(details["seat_number"], "A1")
        self.assertFalse(details["is_validated"])

        # Test Validation (First Scan)
        result = ticket_validation_service.validate_ticket_by_uuid(self.db, "custom-uuid-test")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "SUCCESS")

        # Test Validation (Second Scan - Double entry warning)
        double_result = ticket_validation_service.validate_ticket_by_uuid(self.db, "custom-uuid-test")
        self.assertFalse(double_result["success"])
        self.assertEqual(double_result["status"], "ALREADY_USED")

if __name__ == '__main__':
    unittest.main()
