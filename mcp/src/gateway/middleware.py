"""
MCP Gateway Middleware
"""

from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from prometheus_client import Counter, Histogram, Gauge


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting metrics"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Prometheus metrics
        self.request_count = Counter('mcp_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
        self.request_latency = Histogram('mcp_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
        self.active_requests = Gauge('mcp_active_requests', 'Active requests')
        
        # For internal tracking
        self._internal_request_count = 0
        self._internal_error_count = 0
        self._internal_total_latency = 0.0
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()
        self._internal_request_count += 1
        self.active_requests.inc()
        
        method = request.method
        endpoint = request.url.path
        
        try:
            response = await call_next(request)
            status = response.status_code
            
            # Update Prometheus metrics
            self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
            self.request_latency.labels(method=method, endpoint=endpoint).observe(time.time() - start_time)
            
            return response
        except Exception as e:
            self._internal_error_count += 1
            self.request_count.labels(method=method, endpoint=endpoint, status=500).inc()
            raise
        finally:
            latency = time.time() - start_time
            self._internal_total_latency += latency
            self.active_requests.dec()


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