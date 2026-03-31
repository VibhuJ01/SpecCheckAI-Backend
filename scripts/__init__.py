import logging as logger
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from scripts.rate_limiter import global_rate_limiter, limiter
from src.cred import Credentials
from src.enums import Environments
from src.mongodb.base import BaseDatabase

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def create_app():
    app = FastAPI()

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(GlobalRateLimitMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"is_successful": False, "message": "Too many requests. Please slow down."},
        )

    # Configure the upload folder and maximum content length
    app.add_middleware(UploadSizeLimitMiddleware)

    # Origin validation middleware
    allowed_origins = [
        "https://www.speccheckai.in",
    ]
    if Credentials.environment != Environments.PRODUCTION:
        allowed_origins.extend(["http://localhost:3000", "https://speccheckaiuat.iappc.in"])
    app.add_middleware(OriginValidationMiddleware, allowed_origins=allowed_origins)

    # CORS setup
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            # "Cache-Control",
        ],
    )

    logger.basicConfig(level=logger.INFO)

    # Handler for KeyError
    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        logger.error(f"KeyError: {exc}")
        return JSONResponse(
            status_code=400,
            content={"is_successful": False, "message": f"Missing required field {exc}"},
        )

    # Ensure MongoDB indexes
    BaseDatabase.ensure_indexes()

    prefix = "/api"

    from scripts.authentication import router as authentication
    from scripts.company_master import router as company_master
    from scripts.general_config import router as general_config
    from scripts.log_manager import router as log_master
    from scripts.masters.client_master import router as client_master
    from scripts.masters.department_master import router as department_master
    from scripts.masters.employee_master import router as employee_master
    from scripts.masters.specification_matrix import router as specification_matrix
    from scripts.masters.team_master import router as team_master
    from scripts.super_admin_master import router as super_admin_master

    app.include_router(authentication, prefix=prefix)
    app.include_router(super_admin_master, prefix=prefix + "/super_admin_master")
    app.include_router(employee_master, prefix=prefix + "/employee_master")
    app.include_router(company_master, prefix=prefix + "/company_master")
    app.include_router(client_master, prefix=prefix + "/client_master")
    app.include_router(department_master, prefix=prefix + "/department_master")
    app.include_router(specification_matrix, prefix=prefix + "/specification_matrix")
    app.include_router(team_master, prefix=prefix + "/team_master")
    app.include_router(log_master, prefix=prefix + "/log_manager")
    app.include_router(general_config, prefix=prefix + "/general_config")

    return app


class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > MAX_UPLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "is_successful": False,
                        "message": f"File size exceeds {MAX_UPLOAD_SIZE / (1024 * 1024)} MB limit",
                    },
                )
        return await call_next(request)


class OriginValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_origins: list[str]):
        super().__init__(app)
        self.allowed_origins = allowed_origins

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        # Check if origin matches any allowed origins
        origin_valid = origin in self.allowed_origins if origin else False

        # Check if referer starts with any allowed origins
        referer_valid = any(referer.startswith(o) for o in self.allowed_origins) if referer else False

        if not (origin_valid or referer_valid):
            return JSONResponse(
                status_code=403,
                content={"is_successful": False, "message": "Invalid request origin"},
            )

        return await call_next(request)


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce global rate limiting."""

    async def dispatch(self, request: Request, call_next):
        """Check global rate limit before processing request."""
        is_allowed, info = await global_rate_limiter.is_allowed()

        if not is_allowed:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "is_successful": False,
                    "message": "Global rate limit exceeded. Please try again later.",
                    "limit_info": {
                        "global_limit": info["limit"],
                        # "reset_at": info["reset"],
                    },
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["reset"] - int(time.time())),
                },
            )

        # Add rate limit info to response headers
        response = await call_next(request)
        response.headers["X-RateLimit-Global-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Global-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Global-Reset"] = str(info["reset"])

        return response
