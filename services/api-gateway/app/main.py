from typing import Any
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from app.core.config import settings
from app.core.gateway import gateway_handler
import time

app = FastAPI(title="AI JobMate API Gateway")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)

# Metrics
if settings.ENABLE_METRICS:
    REQUEST_COUNT = Counter(
        'gateway_request_count',
        'Total request count',
        ['method', 'endpoint', 'status']
    )
    REQUEST_LATENCY = Histogram(
        'gateway_request_latency_seconds',
        'Request latency in seconds',
        ['method', 'endpoint']
    )

@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.
    """
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.
    """
    if not settings.ENABLE_METRICS:
        return Response("Metrics disabled")
    return Response(generate_latest())

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway_route(request: Request) -> Any:
    """
    Main gateway route - handles all incoming requests.
    """
    start_time = time.time()
    
    try:
        # Forward request to appropriate service
        response = await gateway_handler.handle_request(request)
        
        # Return response
        content = response.content
        status_code = response.status_code
        headers = dict(response.headers)
        
        # Record metrics
        if settings.ENABLE_METRICS:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(time.time() - start_time)
        
        return Response(
            content=content,
            status_code=status_code,
            headers=headers
        )
        
    except Exception as e:
        # Record error metrics
        if settings.ENABLE_METRICS:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=500
            ).inc()
        raise e

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown.
    """
    await gateway_handler.close()