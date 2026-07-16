from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel
import time
from datetime import datetime
from lambda_service.payment_processor_handler import lambda_handler as payment_handler

# Set docs_url=None to override with our custom Swagger UI endpoint
app = FastAPI(title="Microservicio de Pagos (Simulado)", version="1.0", docs_url=None)

# Telemetry data structure specific to payments
telemetry_data = {
    "total_calls": 0,
    "successful_calls": 0,
    "failed_calls": 0,
    "avg_duration_ms": 0.0,
    "max_duration_ms": 0.0,
    "history": []  # List of recent payment attempts
}

# Timestamps for calculating RPM (Requests Per Minute)
invocation_timestamps = []

def record_telemetry(payload: dict, status_code: int, response: dict, duration_ms: float):
    now = datetime.now()
    timestamp_str = now.strftime("%H:%M:%S")
    
    # Track RPM
    now_ts = now.timestamp()
    invocation_timestamps.append(now_ts)
    
    # Cleanup old timestamps (older than 60s)
    while invocation_timestamps and invocation_timestamps[0] < now_ts - 60:
        invocation_timestamps.pop(0)
        
    telemetry_data["total_calls"] += 1
    
    is_success = response.get("success", False) if isinstance(response, dict) else False
    if is_success:
        telemetry_data["successful_calls"] += 1
    else:
        telemetry_data["failed_calls"] += 1
        
    # Calculate average duration
    total = telemetry_data["total_calls"]
    current_avg = telemetry_data["avg_duration_ms"]
    telemetry_data["avg_duration_ms"] = ((current_avg * (total - 1)) + duration_ms) / total
    
    if duration_ms > telemetry_data["max_duration_ms"]:
        telemetry_data["max_duration_ms"] = duration_ms
        
    # Insert invocation in history
    telemetry_data["history"].insert(0, {
        "timestamp": timestamp_str,
        "payload": payload,
        "status_code": status_code,
        "response": response,
        "duration_ms": round(duration_ms, 2)
    })
    
    # Keep only the last 30 records
    if len(telemetry_data["history"]) > 30:
        telemetry_data["history"].pop()

def get_current_rpm():
    now_ts = datetime.now().timestamp()
    while invocation_timestamps and invocation_timestamps[0] < now_ts - 60:
        invocation_timestamps.pop(0)
    return len(invocation_timestamps)


class PaymentPayload(BaseModel):
    order_id: int
    amount: float
    card_number: str
    cvc: str
    exp_month: int
    exp_year: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "order_id": 1,
                "amount": 25.50,
                "card_number": "4000 1234 5678 9010",
                "cvc": "123",
                "exp_month": 7,
                "exp_year": 2026
            }
        }
    }

@app.post("/payment")
async def invoke_payment(payload: PaymentPayload):
    """
    Simulates payment capture via External Stripe API.
    """
    start_time = time.time()
    event = payload.model_dump()
    status_code = 200
    response_body = {}
    try:
        # Run payment handler logic
        result = payment_handler(event, None)
        status_code = result["statusCode"]
        response_body = result["body"]
        
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail=response_body)
        return response_body
    except HTTPException as he:
        status_code = he.status_code
        response_body = he.detail
        raise he
    except Exception as e:
        status_code = 500
        response_body = {"success": False, "message": str(e)}
        raise HTTPException(status_code=500, detail=response_body)
    finally:
        duration_ms = (time.time() - start_time) * 1000
        record_telemetry(event, status_code, response_body, duration_ms)

@app.get("/telemetry")
async def get_telemetry():
    """
    Returns live statistics and telemetry data.
    """
    return {
        "total_calls": telemetry_data["total_calls"],
        "successful_calls": telemetry_data["successful_calls"],
        "failed_calls": telemetry_data["failed_calls"],
        "avg_duration_ms": round(telemetry_data["avg_duration_ms"], 2),
        "max_duration_ms": round(telemetry_data["max_duration_ms"], 2),
        "rpm": get_current_rpm(),
        "history": telemetry_data["history"]
    }

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Renders custom Swagger UI with embedded Telemetry Dashboard.
    """
    html_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - API Docs & Telemetría",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )
    
    html_content = html_response.body.decode("utf-8")
    
    # Custom HTML telemetry dashboard card to inject in Swagger
    custom_telemetry_ui = """
    <!-- Custom Telemetry Dashboard inside Swagger UI -->
    <div id="swagger-telemetry-panel" style="max-width: 1460px; margin: 20px auto; padding: 24px; font-family: 'Inter', sans-serif; background: #0B0F19; border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; color: #F3F4F6; box-shadow: 0 10px 40px rgba(0,0,0,0.5);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">💳</span>
                <h2 style="font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 20px; margin: 0; background: linear-gradient(to right, #818CF8, #EF4444); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    MONITOR DE TELEMETRÍA DE PAGOS (MICROSERVICIO)
                </h2>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 8px; height: 8px; background-color: #EF4444; border-radius: 50%; display: inline-block; animation: pulse 1.5s infinite;"></span>
                <span style="font-size: 12px; color: #9CA3AF; font-weight: 600;">Monitoreo en Vivo (HTTP)</span>
            </div>
        </div>
        
        <style>
            @keyframes pulse {
                0% { transform: scale(0.9); opacity: 0.5; }
                50% { transform: scale(1.2); opacity: 1; }
                100% { transform: scale(0.9); opacity: 0.5; }
            }
            .sw-metric-card {
                background: rgba(17, 24, 39, 0.7);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 14px 20px;
                text-align: center;
                backdrop-filter: blur(12px);
            }
            .sw-feed-item {
                border-bottom: 1px solid rgba(255,255,255,0.05);
                padding: 10px;
                cursor: pointer;
                border-radius: 8px;
                transition: background-color 0.2s;
                margin-bottom: 8px;
            }
            .sw-feed-item:hover {
                background: rgba(255, 255, 255, 0.02);
            }
            .sw-feed-body {
                font-family: monospace;
                font-size: 11px;
                background-color: rgba(0, 0, 0, 0.4);
                border-radius: 6px;
                padding: 10px;
                color: #A5B4FC;
                overflow-x: auto;
                display: none;
                margin-top: 8px;
                text-align: left;
                border: 1px solid rgba(255,255,255,0.03);
                white-space: pre-wrap;
            }
        </style>
        
        <!-- Metrics Row -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
            <div class="sw-metric-card">
                <div style="font-size: 11px; color: #9CA3AF; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Peticiones Totales</div>
                <div id="sw-m-total" style="font-size: 28px; font-weight: 800; color: #fff; margin-top: 4px;">0</div>
            </div>
            <div class="sw-metric-card">
                <div style="font-size: 11px; color: #9CA3AF; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Pagos Aprobados</div>
                <div id="sw-m-payment" style="font-size: 28px; font-weight: 800; color: #10B981; margin-top: 4px;">0</div>
            </div>
            <div class="sw-metric-card">
                <div style="font-size: 11px; color: #9CA3AF; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Pagos Declinados</div>
                <div id="sw-m-generator" style="font-size: 28px; font-weight: 800; color: #EF4444; margin-top: 4px;">0</div>
            </div>
            <div class="sw-metric-card">
                <div style="font-size: 11px; color: #9CA3AF; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Frecuencia (RPM)</div>
                <div id="sw-m-rpm" style="font-size: 28px; font-weight: 800; color: #F59E0B; margin-top: 4px;">0 req/m</div>
            </div>
            <div class="sw-metric-card">
                <div style="font-size: 11px; color: #9CA3AF; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Latencia Media</div>
                <div id="sw-m-avg" style="font-size: 28px; font-weight: 800; color: #38BDF8; margin-top: 4px;">0 ms</div>
            </div>
        </div>
        
        <!-- Live Layout: Chart + Live Feed -->
        <div style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 24px; align-items: start;">
            <!-- Chart Panel -->
            <div style="background: rgba(17, 24, 39, 0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 14px; padding: 16px;">
                <h4 style="margin: 0 0 12px 0; font-size: 13px; color: #E5E7EB; font-weight: 600;">📈 Carga del Microservicio de Pagos (RPM)</h4>
                <canvas id="swRpmChart" width="400" height="180" style="width: 100%; height: 180px; background: rgba(0,0,0,0.2); border-radius: 8px;"></canvas>
            </div>
            <!-- Feed Panel -->
            <div style="background: rgba(17, 24, 39, 0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 14px; padding: 16px;">
                <h4 style="margin: 0 0 12px 0; font-size: 13px; color: #E5E7EB; font-weight: 600;">📋 Log Transaccional en Tiempo Real</h4>
                <div id="sw-feed-list" style="max-height: 180px; overflow-y: auto; font-size: 12px; color: #9CA3AF; padding-right: 4px;">
                    <div style="text-align: center; padding: 40px 0;">Esperando solicitudes de pago...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Wait for page load, then inject the panel directly above the Swagger UI content
        window.addEventListener('load', function() {
            let attempts = 0;
            const injectInterval = setInterval(function() {
                const target = document.querySelector('#swagger-ui');
                const panel = document.getElementById('swagger-telemetry-panel');
                if (target && panel) {
                    clearInterval(injectInterval);
                    target.parentNode.insertBefore(panel, target);
                    initTelemetry();
                }
                attempts++;
                if (attempts > 20) clearInterval(injectInterval); // Fail safe
            }, 100);
        });
        
        let swRpmHistory = Array(30).fill(0);
        
        function toggleSwDetails(el) {
            const body = el.querySelector('.sw-feed-body');
            if(body) {
                body.style.display = body.style.display === 'block' ? 'none' : 'block';
            }
        }
        
        function drawSwChart() {
            const canvas = document.getElementById('swRpmChart');
            if(!canvas) return;
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Grid lines
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
            ctx.lineWidth = 1;
            for(let i = 0; i <= 4; i++) {
                let y = canvas.height * (i / 4);
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }
            
            // Plot RPM values
            ctx.strokeStyle = '#EF4444';
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            let maxVal = Math.max(...swRpmHistory, 10);
            
            for(let i = 0; i < swRpmHistory.length; i++) {
                let x = canvas.width * (i / (swRpmHistory.length - 1));
                let y = canvas.height - (canvas.height * (swRpmHistory[i] / maxVal) * 0.75) - 10;
                if(i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            
            // Area Fill under the line
            ctx.fillStyle = 'rgba(239, 68, 68, 0.05)';
            ctx.lineTo(canvas.width, canvas.height);
            ctx.lineTo(0, canvas.height);
            ctx.closePath();
            ctx.fill();
        }
        
        async function fetchSwTelemetry() {
            try {
                const res = await fetch('/telemetry');
                if(!res.ok) return;
                const data = await res.json();
                
                document.getElementById('sw-m-total').innerText = data.total_calls;
                document.getElementById('sw-m-payment').innerText = data.successful_calls;
                document.getElementById('sw-m-generator').innerText = data.failed_calls;
                document.getElementById('sw-m-rpm').innerText = `${data.rpm} req/m`;
                document.getElementById('sw-m-avg').innerText = `${data.avg_duration_ms} ms`;
                
                swRpmHistory.push(data.rpm);
                swRpmHistory.shift();
                drawSwChart();
                
                const feed = document.getElementById('sw-feed-list');
                if(data.history.length === 0) {
                    feed.innerHTML = '<div style="text-align: center; padding: 40px 0; color: #6B7280;">Esperando solicitudes de pago...</div>';
                    return;
                }
                
                let html = '';
                data.history.forEach(item => {
                    const isSuccess = item.response && item.response.success;
                    const statusText = isSuccess ? '🟢 200 OK (Aprobado)' : `🔴 Declinado / Error`;
                    const summary = `Pago Orden #${item.payload.order_id} - $${item.payload.amount}`;
                    
                    html += `
                        <div class="sw-feed-item" onclick="toggleSwDetails(this)">
                            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px;">
                                <strong style="color: #EF4444; font-family: sans-serif; letter-spacing: 0.5px;">PAYMENT PROCESSOR</strong>
                                <span style="color: #9CA3AF;">${item.timestamp}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                                <span style="color: #F3F4F6; font-weight: 600;">${summary}</span>
                                <span>${statusText} (${item.duration_ms}ms)</span>
                            </div>
                            <div class="sw-feed-body">
                                <strong>Request Payload:</strong><br>
                                ${JSON.stringify(item.payload, null, 2)}
                                <br><br>
                                <strong>Response:</strong><br>
                                ${JSON.stringify(item.response, null, 2)}
                            </div>
                        </div>
                    `;
                });
                feed.innerHTML = html;
            } catch(e) {
                console.error(e);
            }
        }
        
        function initTelemetry() {
            drawSwChart();
            fetchSwTelemetry();
            setInterval(fetchSwTelemetry, 1000);
        }
    </script>
    """
    
    modified_html_str = html_content.replace("</body>", custom_telemetry_ui + "</body>")
    return HTMLResponse(content=modified_html_str, status_code=200)

@app.get("/", response_class=HTMLResponse)
async def get_root_redirect():
    """
    Redirects root to the Swagger UI custom documentation.
    """
    return """
    <html>
        <head><script>window.location.href = '/docs';</script></head>
        <body>Redireccionando al panel de Swagger...</body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
