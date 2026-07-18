import traceback
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import json

class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            
            # Log all API requests
            with open("api_debug.log", "a") as f:
                f.write(f"REQ: {request.method} {request.url.path} -> STATUS {response.status_code}\n")
                
            return response
        except Exception as e:
            tb = traceback.format_exc()
            with open("api_debug.log", "a") as f:
                f.write(f"Exception on {request.url.path}:\n{tb}\n\n")
            raise e
