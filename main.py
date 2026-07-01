import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ==========================================
# Middleware 2: CORS Configuration
# ==========================================
ALLOWED_ORIGINS = [
    "https://exam.sanand.workers.dev/tds-2026-05-ga2#hq-config-precedence-server",
    "YOUR_EXAM_PORTAL_ORIGIN_HERE" # <--- REPLACE WITH YOUR EXAM PAGE'S EXACT URL
]

# CORSMiddleware automatically handles OPTIONS (preflight) requests safely
# It specifically prevents wildcard (*) headers when a list is provided.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory dictionary to bucket requests by X-Client-Id
rate_limits = defaultdict(list)

@app.middleware("http")
async def context_and_rate_limit_middleware(request: Request, call_next):
    # ==========================================
    # Middleware 1: Request Context (Incoming)
    # ==========================================
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = str(uuid.uuid4())
    
    # Propagate to endpoint via request state
    request.state.request_id = req_id

    # ==========================================
    # Middleware 3: Per-Client Rate Limiter
    # ==========================================
    client_id = request.headers.get("X-Client-Id")
    if client_id:
        now = time.time()
        
        # Purge timestamps older than our 10-second window
        rate_limits[client_id] = [t for t in rate_limits[client_id] if now - t < 10]
        
        # Check Bucket Limit (Assigned: 11 req / 10s)
        if len(rate_limits[client_id]) >= 11:
            response = JSONResponse({"detail": "Too Many Requests"}, status_code=429)
            # Ensure the X-Request-ID still gets attached to rate-limited responses
            response.headers["X-Request-ID"] = req_id
            return response
            
        rate_limits[client_id].append(now)

    # Process the valid request
    response = await call_next(request)

    # ==========================================
    # Middleware 1: Request Context (Outgoing)
    # ==========================================
    response.headers["X-Request-ID"] = req_id
    return response

# ==========================================
# Endpoint
# ==========================================
@app.get("/ping")
async def ping_endpoint(request: Request):
    return {
        "email": "22ds2000150@ds.study.iitm.ac.in",
        "request_id": request.state.request_id
    }
