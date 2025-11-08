"""
Request and Response Signing for MCP Gateway

Implements cryptographic signing of requests and responses for security.
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

class SigningConfig:
    """Configuration for request/response signing"""
    def __init__(
        self,
        enabled: bool = True,
        algorithm: str = "ed25519",
        key_rotation_hours: int = 24
    ):
        self.enabled = enabled
        self.algorithm = algorithm
        self.key_rotation_hours = key_rotation_hours

class RequestSigner:
    """Signs outgoing requests to tool endpoints"""
    
    def __init__(self, config: SigningConfig):
        self.config = config
        if config.enabled:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()
            
    def sign_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign request data with current key
        
        Args:
            data: Request payload to sign
            
        Returns:
            Dict with signed data and signature
        """
        if not self.config.enabled:
            return data
            
        # Add timestamp to prevent replay attacks
        data["_timestamp"] = int(time.time())
        
        # Create canonical string
        canonical = json.dumps(data, sort_keys=True)
        
        # Sign with Ed25519
        signature = self._private_key.sign(canonical.encode())
        
        # Add signature to request
        data["_signature"] = base64.b64encode(signature).decode()
        
        return data
        
    def rotate_keys(self):
        """Generate new signing keys"""
        if self.config.enabled:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()
            
class ResponseSigner:
    """Signs responses from the gateway"""
    
    def __init__(self, config: SigningConfig):
        self.config = config
        if config.enabled:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()
            
    def sign_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign response data
        
        Args:
            data: Response payload to sign
            
        Returns:
            Dict with signed data and signature
        """
        if not self.config.enabled:
            return data
            
        # Add timestamp
        data["_timestamp"] = int(time.time())
        
        # Create canonical string
        canonical = json.dumps(data, sort_keys=True)
        
        # Sign with Ed25519
        signature = self._private_key.sign(canonical.encode())
        
        # Add signature to response
        data["_signature"] = base64.b64encode(signature).decode()
        
        return data
        
    def verify_signature(
        self,
        data: Dict[str, Any],
        signature: str,
        public_key: bytes
    ) -> bool:
        """
        Verify response signature
        
        Args:
            data: Response data
            signature: Base64 encoded signature
            public_key: Ed25519 public key bytes
            
        Returns:
            bool: True if signature is valid
        """
        if not self.config.enabled:
            return True
            
        try:
            # Remove signature from data for verification
            verify_data = data.copy()
            del verify_data["_signature"]
            
            # Create canonical string
            canonical = json.dumps(verify_data, sort_keys=True)
            
            # Load public key
            key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
            
            # Verify signature
            key.verify(
                base64.b64decode(signature),
                canonical.encode()
            )
            return True
            
        except (InvalidSignature, KeyError, ValueError):
            return False
            
    def rotate_keys(self):
        """Generate new signing keys"""
        if self.config.enabled:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()