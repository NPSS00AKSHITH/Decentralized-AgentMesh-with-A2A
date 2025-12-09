import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from .security import SecurityManager, AuthenticationError

class JWTMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, expected_audience: str):
        super().__init__(app)
        self.security = SecurityManager()
        self.expected_audience = expected_audience

    async def dispatch(self, request: Request, call_next):
        # We only care about securing the API endpoints
        # If this middleware is added to the sub-app (a2a_app), every request hits here.
        # If added to main app, we might need to filter.
        # Assuming we add it to the A2A sub-app directly, or filter by path if on main.
        
        # Let's check if it's an OPTIONS request (CORS) - usually we skip auth for OPTIONS
        if request.method == "OPTIONS":
            return await call_next(request)

        # ALLOW DISCOVERY: Skip auth for agent.json
        if "agent.json" in request.url.path:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # Only bypass if explicitly allowed via env var for local dev
            if os.getenv("DISABLE_AUTH", "false").lower() == "true":
                return await call_next(request)
            return JSONResponse({"error": "Unauthorized", "detail": "Missing or invalid Authorization header"}, status_code=401)
        
        parts = auth_header.split(" ")
        if len(parts) != 2:
             return JSONResponse({"error": "Invalid Authorization header format", "detail": "Bearer token required"}, status_code=401)
        token = parts[1]
        try:
            self.security.validate_token(token, self.expected_audience)
        except AuthenticationError as e:
            # FIX: Do not pass! Return 403 Forbidden.
            # Only bypass if explicitly allowed via env var for local dev
            if os.getenv("DISABLE_AUTH", "false").lower() == "true":
                # logger.warning(f"Auth failed but bypassed (DISABLE_AUTH=true): {e}")
                pass 
            else:
                return JSONResponse({"error": "Unauthorized", "detail": str(e)}, status_code=403)
            
        return await call_next(request)
