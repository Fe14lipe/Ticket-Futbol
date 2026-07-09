from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.ticket_validation_service import ticket_validation_service
from fastapi.templating import Jinja2Templates
from app.api.dependencies import RoleChecker, get_current_user
from app.models.user import User
from app.models.seat import Seat
from app.models.event import Event
from app.models.order import Order
from app.models.ticket import Ticket
from app.schemas.ticket_schema import TicketDetailOut
from typing import List

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Role checker for staff (only staff or admins can trigger manual json validation API if needed, 
# but browser scan should load immediately for convenience as requested by user)
staff_or_admin = RoleChecker(["staff", "admin"])

@router.get("/t/{ticket_uuid}", response_class=HTMLResponse)
def view_ticket_details(ticket_uuid: str, request: Request, db: Session = Depends(get_db)):
    """
    Renders the public ticket landing page. Shows the generated QR code, seat info, and game details.
    """
    ticket_details = ticket_validation_service.get_ticket_details(db, ticket_uuid)
    if not ticket_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket details not found. UUID may be invalid."
        )
    
    return templates.TemplateResponse(
        "ticket_view.html", 
        {
            "request": request, 
            "ticket": ticket_details
        }
    )

@router.get("/validate/{ticket_uuid}", response_class=HTMLResponse)
def validate_ticket_scan(ticket_uuid: str, request: Request, db: Session = Depends(get_db)):
    """
    Validation endpoint called when access control staff scans the ticket QR.
    Updates status to used and returns a highly visual success/failure HTML feedback screen.
    """
    result = ticket_validation_service.validate_ticket_by_uuid(db, ticket_uuid)
    
    # We will render a template or inline visual HTML showing state
    color = "#10B981" if result["success"] else "#EF4444" # green or red
    title_text = "ACCESO CONCEDIDO (GRANTED)" if result["success"] else "ACCESO DENEGADO (DENIED)"
    status_icon = "✓" if result["success"] else "✗"
    
    # Render buyer row separately to avoid quote nesting conflict
    buyer_row = ""
    if result.get("buyer_name"):
        buyer_row = f"""
        <div class="info-row">
            <span class="label">Asistente:</span>
            <span class="val">{result.get("buyer_name")}</span>
        </div>
        """

    # Render info box separately
    info_box_html = ""
    if "event_title" in result:
        info_box_html = f"""
        <div class="info-box">
            <div class="info-row">
                <span class="label">Evento:</span>
                <span class="val">{result.get("event_title", "N/A")}</span>
            </div>
            <div class="info-row">
                <span class="label">Asiento:</span>
                <span class="val">{result.get("seat_number", "N/A")}</span>
            </div>
            {buyer_row}
            <div class="info-row">
                <span class="label">UUID del Ticket:</span>
                <span class="val" style="font-family: monospace; font-size: 11px;">{ticket_uuid[:18]}...</span>
            </div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Validación de Boleto - Ticket Futbol</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                background-color: #0F172A;
                color: #F8FAFC;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
                text-align: center;
            }}
            .card {{
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px;
                padding: 40px;
                max-width: 450px;
                width: 100%;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
                box-sizing: border-box;
            }}
            .badge {{
                width: 80px;
                height: 80px;
                border-radius: 50%;
                background-color: {color};
                color: white;
                font-size: 40px;
                line-height: 80px;
                margin: 0 auto 24px auto;
                font-weight: bold;
                box-shadow: 0 0 20px {color}80;
            }}
            h1 {{
                font-size: 24px;
                font-weight: 800;
                margin-bottom: 8px;
                color: {color};
            }}
            .msg {{
                font-size: 16px;
                color: #94A3B8;
                margin-bottom: 24px;
                line-height: 1.5;
            }}
            .info-box {{
                background: rgba(15, 23, 42, 0.5);
                border-radius: 16px;
                padding: 20px;
                text-align: left;
                margin-bottom: 24px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 12px;
                font-size: 14px;
            }}
            .info-row:last-child {{
                margin-bottom: 0;
            }}
            .label {{
                color: #64748B;
            }}
            .val {{
                font-weight: 600;
                color: #E2E8F0;
            }}
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
                color: white;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 14px;
                transition: transform 0.2s, box-shadow 0.2s;
                width: 100%;
                box-sizing: border-box;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">{status_icon}</div>
            <h1>{title_text}</h1>
            <p class="msg">{result["message"]}</p>
            
            {info_box_html}
            
            <a href="/static/index.html" class="btn">Volver al Portal</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@router.post("/validate-json/{ticket_uuid}", status_code=status.HTTP_200_OK)
def validate_ticket_json(
    ticket_uuid: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_or_admin)
):
    """
    JSON API for scanning tickets. Restricts usage to access control staff/admin.
    Used by validation application/scanner.
    """
    result = ticket_validation_service.validate_ticket_by_uuid(db, ticket_uuid)
    if not result["success"]:
        if result["status"] == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.get("/my", response_model=List[TicketDetailOut])
def get_user_tickets(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all tickets purchased by the authenticated user.
    If admin, retrieves all tickets in the system.
    """
    if current_user.role == "admin":
        orders = db.query(Order).filter(Order.status == "PAID").all()
    else:
        orders = db.query(Order).filter(Order.user_id == current_user.id, Order.status == "PAID").all()
        
    if not orders:
        return []
    
    order_ids = [o.id for o in orders]
    tickets = db.query(Ticket).filter(Ticket.order_id.in_(order_ids)).all()
    
    out = []
    for t in tickets:
        seat = db.query(Seat).filter(Seat.id == t.seat_id).first()
        event = db.query(Event).filter(Event.id == seat.event_id).first() if seat else None
        
        # Get actual buyer info
        order = db.query(Order).filter(Order.id == t.order_id).first()
        buyer = db.query(User).filter(User.id == order.user_id).first() if order else None
        
        out.append(TicketDetailOut(
            ticket_uuid=t.ticket_uuid,
            event_title=event.title if event else "Unknown Match",
            event_date=event.date if event else None,
            event_location=event.location if event else "Unknown Location",
            seat_number=seat.seat_number if seat else "N/A",
            qr_code_url=t.qr_code_url,
            is_validated=t.is_validated,
            validated_at=t.validated_at,
            buyer_name=buyer.full_name if buyer else "Unknown Buyer"
        ))
    return out
