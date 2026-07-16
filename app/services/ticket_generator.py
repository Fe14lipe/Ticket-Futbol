import os
import logging
import qrcode

logger = logging.getLogger(__name__)

class TicketGeneratorService:
    def generate_qr_code(self, ticket_uuid: str, ticket_url: str) -> str:
        """
        Generates the ticket QR Code directly inside the Queue Worker process
        using the python qrcode library.
        """
        logger.info(f"Generating QR Code locally for ticket {ticket_uuid} with URL {ticket_url}")
        
        # Check target directories to write to
        base_dirs = ["/app/static/qrcodes", "./static/qrcodes", "../static/qrcodes"]
        target_dir = None
        for d in base_dirs:
            try:
                os.makedirs(d, exist_ok=True)
                target_dir = d
                break
            except Exception:
                continue
                
        if not target_dir:
            target_dir = "./qrcodes"
            os.makedirs(target_dir, exist_ok=True)
            
        file_path = os.path.join(target_dir, f"{ticket_uuid}.png")
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(ticket_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF")
            img.save(file_path)
            
            logger.info(f"QR Code successfully generated and saved to {file_path}")
            return f"/static/qrcodes/{ticket_uuid}.png"
        except Exception as e:
            logger.error(f"Error generating QR code for ticket {ticket_uuid}: {e}")
            return f"/static/qrcodes/{ticket_uuid}.png"

ticket_generator_service = TicketGeneratorService()
