from fastapi import FastAPI, HTTPException, Request
from lambda_service.payment_processor_handler import lambda_handler as payment_handler
from lambda_service.ticket_generator_handler import lambda_handler as generator_handler

app = FastAPI(title="AWS Lambda Simulator Runner", version="1.0")

@app.post("/payment")
async def invoke_payment(payload: Request):
    """
    Simulates calling payment Lambda.
    """
    event = await payload.json()
    result = payment_handler(event, None)
    
    if result["statusCode"] != 200:
        raise HTTPException(status_code=result["statusCode"], detail=result["body"])
    
    return result["body"]

@app.post("/generate_ticket")
async def invoke_generator(payload: Request):
    """
    Simulates calling ticket generator Lambda.
    """
    event = await payload.json()
    result = generator_handler(event, None)
    
    if result["statusCode"] != 200:
        raise HTTPException(status_code=result["statusCode"], detail=result["body"])
    
    return result["body"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
