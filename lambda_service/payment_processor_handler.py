import time
import uuid

def lambda_handler(event, context):
    """
    Simulated AWS Lambda function for payment processing.
    Expects event payload containing order_id, amount, and payment credentials.
    """
    order_id = event.get("order_id")
    amount = event.get("amount")
    card_number = event.get("card_number")
    cvc = event.get("cvc")

    print(f"[Lambda Payment] Processing payment for Order ID: {order_id}, Amount: ${amount}")

    # Basic validations
    if not order_id or not amount or not card_number or not cvc:
        return {
            "statusCode": 400,
            "body": {
                "success": False,
                "message": "Missing payment fields (order_id, amount, card_number, cvc)"
            }
        }

    # Simulate network latency of payment processor API (Stripe/Authorize.Net)
    time.sleep(1.2)

    # Simple logic to simulate payment declines
    if card_number.replace(" ", "").startswith("4111"):
        # Simulated decline for card starting with 4111
        return {
            "statusCode": 200,
            "body": {
                "success": False,
                "message": "Card declined. Insufficient funds."
            }
        }
    
    if cvc == "999":
        # Simulated gate crash CVV
        return {
            "statusCode": 200,
            "body": {
                "success": False,
                "message": "Invalid CVV security code."
            }
        }

    # Successful payment simulation
    transaction_id = f"ch_{uuid.uuid4().hex[:20]}"
    return {
        "statusCode": 200,
        "body": {
            "success": True,
            "transaction_id": transaction_id,
            "message": "Payment captured successfully."
        }
    }
