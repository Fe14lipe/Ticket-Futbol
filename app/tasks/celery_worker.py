import logging
from celery import Celery
from app.core.config import settings
from app.db.database import SessionLocal
from app.db import base
from app.models.ticket import Ticket
from app.services.ticket_generator import ticket_generator_service

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "tasks", 
    broker=settings.CELERY_BROKER_URL, 
    backend=settings.CELERY_RESULT_BACKEND
)

# Optional configuration overrides
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=4 # Performance & concurrency limit control
)

@celery_app.task(name="tasks.generate_ticket_task")
def generate_ticket_task(ticket_id: int):
    """
    Celery task that runs asynchronously to generate a QR Code ticket by calling
    the simulated Serverless Lambda component.
    """
    logger.info(f"Asynchronous task started: generating ticket ID {ticket_id}")
    
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.error(f"Ticket ID {ticket_id} not found in database. Generation aborted.")
            return False

        # In production, this would represent the public URL of the ticket
        # E.g., http://gateway-host/t/{uuid}
        # Locally, we use a relative path /t/{uuid} or absolute URL
        ticket_url = f"/t/{ticket.ticket_uuid}"
        
        # Generate QR Code locally in the worker
        qr_url = ticket_generator_service.generate_qr_code(ticket.ticket_uuid, ticket_url)
        
        # Save to database
        ticket.qr_code_url = qr_url
        db.commit()
        
        logger.info(f"Asynchronous QR generation complete for ticket ID {ticket_id}. Path: {qr_url}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in Celery worker task for ticket ID {ticket_id}: {e}")
        return False
    finally:
        db.close()
