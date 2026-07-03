import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ==========================================
# Middleware 2: Strict CORS Policy
# ==========================================
ALLOWED_ORIGINS = [
    "https://app-1m57wz.example.com",
    "https://exam.sanand.workers.dev" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Global State for Rate Limiting
client_requests = defaultdict(list)
RATE_LIMIT = 11
WINDOW_SECONDS = 10

# ==========================================
# Middlewares 1 & 3: Context & Rate Limiting
# ==========================================
@app.middleware("http")
async def combined_middleware(request: Request, call_next):
    # --- Middleware 1: Context Propagator ---
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = str(uuid.uuid4())
        
    # Store it in the state so the endpoint can read it
    request.state.request_id = req_id

    # Ignore OPTIONS preflight checks for the rate limiter
    if request.method == "OPTIONS":
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # --- Middleware 3: Per-Client Rate Limiting ---
    client_id = request.headers.get("X-Client-Id")
    if client_id:
        now = time.time()
        # Clean up old requests outside the 10-second window
        client_requests[client_id] = [t for t in client_requests[client_id] if now - t < WINDOW_SECONDS]
        
        # Check if they exceeded 11 requests
        if len(client_requests[client_id]) >= RATE_LIMIT:
            
            # Prepare headers (Context Propagator requirement)
            headers = {"X-Request-ID": req_id}
            
            # CRITICAL FIX: Manually inject CORS headers into the 429 response
            # Only give the ACAO header if they are in the allowed origins whitelist!
            origin = request.headers.get("origin")
            if origin in ALLOWED_ORIGINS:
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Expose-Headers"] = "X-Request-ID"
                
            return JSONResponse(
                content={"error": "Too Many Requests"},
                status_code=429,
                headers=headers
            )
            
        client_requests[client_id].append(now)

    # Proceed to the endpoint
    response = await call_next(request)
    
    # Ensure every single response gets the X-Request-ID header attached
    response.headers["X-Request-ID"] = req_id
    return response

# ==========================================
# Endpoint
# ==========================================
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "22ds2000150@ds.study.iitm.ac.in",
        "request_id": request.state.request_id
    }
