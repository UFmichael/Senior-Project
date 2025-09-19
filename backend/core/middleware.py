import time
from starlette.middleware.base import BaseHTTPMiddleware

class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """
    Measures request→response time and adds an X-Response-Time header.
    """
     
    async def dispatch(self, request, call_next):
        start = time.time() 
        response = await call_next(request)
        elapsed_ms = (time.time() - start) * 1000
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        return response