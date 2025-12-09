import os
import jwt
import time
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

class AuthenticationError(Exception):
    pass

class TokenExpiredError(AuthenticationError):
    pass

class SecurityManager:
    """
    Centralized security logic for A2A authentication.
    """
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET")
        if not self.jwt_secret:
            # logger.warning("JWT_SECRET not set! Using insecure default 'dev-shared-secret'.")
            self.jwt_secret = "dev-shared-secret"
        self.algorithm = "HS256"

    def generate_token(self, source_agent: str, target_agent: str, correlation_id: str) -> str:
        """
        Creates a short-lived JWT for service-to-service calls.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "iss": source_agent,       # Issuer
            "aud": target_agent,       # Audience
            "cid": correlation_id,     # Traceability
            "iat": now.timestamp(),    # Issued At
            "exp": (now + timedelta(minutes=5)).timestamp() # 5 minute expiry
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.algorithm)

    def validate_token(self, token: str, expected_audience: str) -> Dict[str, Any]:
        """
        Validates a received JWT. Raises exception if invalid or expired.
        """
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.algorithm],
                audience=expected_audience,
                leeway=30
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidAudienceError:
            raise AuthenticationError(f"Token audience mismatch. Expected {expected_audience}")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")