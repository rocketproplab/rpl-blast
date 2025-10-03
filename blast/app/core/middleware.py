"""Request/response middleware"""
import time
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


class TimingMiddleware(BaseHTTPMiddleware):
    """Add response time headers"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


def add_middleware(app: FastAPI):
    """Add custom middleware to FastAPI app"""
    app.add_middleware(TimingMiddleware)