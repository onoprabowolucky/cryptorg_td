import functools
import time
from typing import Callable, Any, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

class TTLCache:
    """Simple TTL-aware LRU cache decorator."""
    cache: dict
    timestamps: dict
    maxsize: int
    ttl: int

    def __init__(self, maxsize: int = 128, ttl: int = 300) -> None:
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}

    def __call__(self, func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = functools._make_key(args, kwargs, typed=False)
            current_time = time.time()

            # Check TTL
            if key in self.timestamps and current_time - self.timestamps[key] > self.ttl:
                del self.cache[key]
                del self.timestamps[key]

            # Cache hit
            if key in self.cache:
                self.timestamps[key] = current_time  # Update timestamp
                return self.cache[key]

            # Cache miss
            result = func(*args, **kwargs)
            if len(self.cache) >= self.maxsize:
                # Evict LRU (simplified: evict oldest)
                oldest_key = min(self.timestamps, key=lambda k: self.timestamps[k])
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            self.cache[key] = result
            self.timestamps[key] = current_time
            return result
        return wrapper

def ttl_cache(maxsize: int = 128, ttl: int = 300) -> Callable[[F], F]:
    """Decorator factory for TTL-aware caching."""
    return TTLCache(maxsize=maxsize, ttl=ttl)

# Example usage:
# @ttl_cache(maxsize=100, ttl=60)
# def expensive_crypto_calculation(data):
#     ...