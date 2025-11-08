"""
MCP Gateway Middleware

This module contains middleware implementations for the MCP Gateway:
- MetricsMiddleware: Collects and exposes Prometheus metrics
- PIIProtectionMiddleware: (Planned) Protection against PII exposure
"""

from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from prometheus_client import Counter, Histogram, Gauge


"""
FastAPI Middleware Components for MCP Gateway

Implements middleware for:
- Metrics collection
- Request tracing
- Security headers
"""

from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import time

class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect Prometheus metrics for requests"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        # Record request duration
        duration = time.time() - start_time
        
        # Update metrics (handled in gateway.py)
        return response

class TracingMiddleware(BaseHTTPMiddleware):
    """OpenTelemetry request tracing"""
    
    def __init__(self, app, tracer: trace.Tracer):
        super().__init__(app)
        self.tracer = tracer
        
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        with self.tracer.start_as_current_span(
            f"{request.method} {request.url.path}"
        ) as span:
            # Add request attributes to span
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.route", request.url.path)
            
            try:
                response = await call_next(request)
                
                # Add response attributes
                span.set_attribute("http.status_code", response.status_code)
                
                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR))
                    
                return response
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                raise

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


class PIIProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware for PII protection"""
    
    PII_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{16}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    ]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # In a real implementation, you would scan request body for PII
        # and either redact it or block the request
        response = await call_next(request)
        return response