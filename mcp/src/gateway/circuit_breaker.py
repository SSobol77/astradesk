"""
Circuit Breaker Implementation for MCP Gateway

Implements the Circuit Breaker pattern to prevent cascading failures
and provide fault tolerance for tool endpoints.
"""

from enum import Enum
from time import time
from threading import Lock
from typing import Optional

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """
    Circuit breaker implementation with three states:
    - CLOSED: Normal operation, requests flow through
    - OPEN: Failing state, reject requests immediately
    - HALF_OPEN: Testing recovery, allow limited requests
    """
    
    def __init__(
        self,
        failure_threshold: int = 50,
        recovery_timeout: int = 30,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time: Optional[float] = None
        self._half_open_successes = 0
        self._lock = Lock()
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
        
    def allow_request(self) -> bool:
        """
        Determine if a request should be allowed through
        
        Returns:
            bool: True if request should be allowed, False if it should be rejected
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
                
            if self._state == CircuitState.OPEN:
                if self._last_failure_time is None:
                    return False
                    
                if time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_successes = 0
                    return True
                    
                return False
                
            if self._state == CircuitState.HALF_OPEN:
                return True
                
        return False
        
    def record_success(self):
        """Record a successful request"""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                self._failure_count = 0
                
            elif self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_requests:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._last_failure_time = None
                    self._half_open_successes = 0
                    
    def record_failure(self):
        """Record a failed request"""
        with self._lock:
            self._last_failure_time = time()
            
            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._half_open_successes = 0