import os
import qrcode
from PIL import Image

def lambda_handler(event, context):
    """
    Simulated AWS Lambda function for generating ticket QR codes.
    Expects event payload containing ticket_uuid and ticket_url.
    """
    ticket_uuid = event.get("ticket_uuid")
    ticket_url = event.get("ticket_url")

    print(f"[Lambda Generator] Generating QR for ticket UUID: {ticket_uuid}")

    if not ticket_uuid or not ticket_url:
        return {
            "statusCode": 400,
            "body": {
                "success": False,
                "message": "Missing ticket fields (ticket_uuid, ticket_url)"
            }
        }

    # Define paths
    # We write to /app/static/qrcodes/ or ./static/qrcodes/ depending on where we are run.
    # In Docker, we will mount a shared volume.
    base_dirs = ["/app/static/qrcodes", "./static/qrcodes", "../static/qrcodes"]
    target_dir = None
    for d in base_dirs:
        # Check if the folder can be created/written to
        try:
            os.makedirs(d, exist_ok=True)
            target_dir = d
            break
        except Exception:
            continue

    if not target_dir:
        # Fail-safe: write in current working directory
        target_dir = "./qrcodes"
        os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, f"{ticket_uuid}.png")

    # Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, # High error correction
        box_size=10,
        border=4,
    )
    
    # We want the QR code to encode the actual server URL (including host/port)
    # The client/access scanner will scan it and load this URL
    # If ticket_url is a relative route like /t/{uuid}, the scanner page will resolve it.
    # For standalone scanner app support, we encode the full URL
    qr.add_data(ticket_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF") # Elegant slate dark color for QR code
    img.save(file_path)

    print(f"[Lambda Generator] QR Code saved to: {file_path}")

    # Return the relative path of the QR code so the browser can fetch it
    return {
        "statusCode": 200,
        "body": {
            "success": True,
            "qr_code_url": f"/static/qrcodes/{ticket_uuid}.png"
        }
    }
