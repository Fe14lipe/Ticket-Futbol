import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class TicketGeneratorService:
    def __init__(self):
        self.lambda_url = f"{settings.LAMBDA_SERVICE_URL}/generate_ticket"

    def generate_qr_code_lambda(self, ticket_uuid: str, ticket_url: str) -> str:
        """
        Invokes the simulated QR Ticket Generator Lambda function.
        Synchronous HTTP client because it is called inside Celery tasks (which run in worker threads).
        """
        payload = {
            "ticket_uuid": ticket_uuid,
            "ticket_url": ticket_url
        }

        try:
            logger.info(f"Invoking ticket generator Lambda for ticket {ticket_uuid} with URL {ticket_url}")
            response = httpx.post(self.lambda_url, json=payload, timeout=15.0)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Ticket generator Lambda response: {data}")
                return data.get("qr_code_url")
            else:
                logger.error(f"Ticket generator Lambda returned status {response.status_code}: {response.text}")
                return f"/static/qrcodes/{ticket_uuid}.png" # Fallback guess path
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Ticket Generator Lambda: {e}")
            # Mock fallback: return local route since it will be generated anyway
            logger.warning("Simulating local fallback path for development environment")
            return f"/static/qrcodes/{ticket_uuid}.png"

ticket_generator_service = TicketGeneratorService()
