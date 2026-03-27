import time
from typing import Optional

import redis.asyncio as redis
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.encryption_system import EncryptionSystem

# Lazily initialized encryption system to avoid creating it at module import time
_encryption_system = None


def _get_encryption_system():
    """Get or create the encryption system singleton."""
    global _encryption_system
    if _encryption_system is None:
        _encryption_system = EncryptionSystem()
    return _encryption_system


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key based on authenticated user or IP address.

    For authenticated users: use email from JWT token
    For anonymous users: use IP address

    This allows multiple users from the same network (e.g., corporate office)
    to have independent rate limits while still protecting against abuse.

    Args:
        request: FastAPI request object

    Returns:
        str: Rate limit key in format "user:<email>" or "ip:<address>"
    """
    try:
        # Try to get auth token from cookies
        auth_token = request.cookies.get("auth_token", "")
        if auth_token:
            encryption_system = _get_encryption_system()
            decoded_data = encryption_system.decrypt_string(encrypted_string=auth_token)
            email = decoded_data.get("email", "")
            if email:
                return f"user:{email}"
    except (ValueError, KeyError, Exception):
        # If token decryption fails, fall back to IP address
        # Catching specific exceptions but also broad Exception to handle cryptography errors
        pass

    # Fall back to IP address for unauthenticated requests
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],
    storage_uri="redis://localhost:6379",
    key_prefix="speccheckai_rate_limit",
)


class GlobalRateLimiter:
    """
    Global rate limiter that applies across all requests regardless of user or IP.
    Uses Redis for distributed counting with sliding window algorithm.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_requests: int = 1000,
        window_seconds: int = 60,
        key_prefix: str = "speccheckai_global_rate_limit",
    ):
        """
        Initialize global rate limiter.

        Args:
            redis_url: Redis connection URL
            max_requests: Maximum number of requests allowed in the time window
            window_seconds: Time window in seconds (default: 60 for 1 minute)
            key_prefix: Prefix for Redis keys
        """
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._redis_client: Optional[redis.Redis] = None

    async def get_redis_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis_client

    async def is_allowed(self) -> tuple[bool, dict]:
        """
        Check if request is allowed under global rate limit.

        Returns:
            tuple: (is_allowed, info_dict)
                - is_allowed: True if request is within limit, False otherwise
                - info_dict: Dictionary with limit info (current, limit, reset_time)
        """
        client = await self.get_redis_client()
        current_time = time.time()
        window_start = current_time - self.window_seconds
        key = f"{self.key_prefix}:requests"

        # Use Redis pipeline for atomic operations
        pipe = client.pipeline()

        # Remove old entries outside the current window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        pipe.zcard(key)

        # Add current request with score as timestamp
        request_id = f"{current_time}:{id(self)}"
        pipe.zadd(key, {request_id: current_time})

        # Set expiry on the key
        pipe.expire(key, self.window_seconds * 2)

        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]  # Count before adding new request

        # Calculate reset time (end of current window)
        reset_time = int(current_time + self.window_seconds)

        info = {
            "limit": self.max_requests,
            "current": current_count,
            "remaining": max(0, self.max_requests - current_count),
            "reset": reset_time,
        }

        is_allowed = current_count < self.max_requests
        return is_allowed, info

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()


global_rate_limiter = GlobalRateLimiter(
    redis_url="redis://localhost:6379",
    max_requests=200,  # Global limit: 200 requests per minute
    window_seconds=60,  # Time window: 1 minute
    key_prefix="speccheckai_global:global",
)
