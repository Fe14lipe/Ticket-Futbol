from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.order import Order
from app.schemas.order_schema import OrderCreate, OrderOut, PaymentRequest, PaymentResponse
from app.services.ticket_service import ticket_service
from app.api.dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_ticket_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a pending purchase order. Holds the requested seats using Redis distributed locks.
    """
    order = ticket_service.create_order(
        db=db,
        user_id=current_user.id,
        event_id=order_in.event_id,
        seat_ids=order_in.seat_ids
    )
    return order

@router.post("/{order_id}/checkout", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
async def checkout_order(
    order_id: int,
    payment_in: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Completes checkout of an order, invoking payment Lambda. Dispatches async Celery task to generate QR codes.
    """
    # Verify order matches
    if payment_in.order_id != order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order ID URL parameter does not match payload JSON"
        )
        
    card_info = {
        "card_number": payment_in.card_number,
        "exp_month": payment_in.exp_month,
        "exp_year": payment_in.exp_year,
        "cvc": payment_in.cvc
    }

    result = await ticket_service.confirm_payment_and_complete_order(
        db=db,
        order_id=order_id,
        user_id=current_user.id,
        card_info=card_info
    )
    
    if result["success"]:
        return PaymentResponse(
            success=True,
            transaction_id=result.get("tickets", [""])[0], # Returning first ticket code as reference
            message=result["message"],
            tickets=result.get("tickets", [])
        )
    else:
        return PaymentResponse(
            success=False,
            transaction_id=None,
            message=result["message"]
        )
