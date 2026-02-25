# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from __future__ import annotations

from copy   import deepcopy
from time   import monotonic
from typing import Awaitable, Callable, Any
import asyncio


class MethodCache:
    """Plugin metodları için RAM tabanlı TTL cache (singleton kullanımı için)."""

    def __init__(self):
        self._cache    : dict[tuple[str, str], dict[str, tuple[float, Any]]] = {}
        self._inflight : dict[tuple[str, str], dict[str, asyncio.Task]]      = {}
        self._lock                                                           = asyncio.Lock()

    async def run(
        self,
        *,
        namespace: str,
        method_name: str,
        key: str,
        producer: Callable[[], Awaitable[Any]],
        should_cache: Callable[[Any], bool] | None = None,
        ttl: int = 3600,
        max_entries: int = 512,
    ):
        """Aynı namespace+method+key çağrıları için TTL cache uygula."""
        if ttl <= 0:
            return self._clone_payload(await producer())

        bucket_key = (namespace, method_name)
        now        = monotonic()

        async with self._lock:
            cache_bucket = self._cache.setdefault(bucket_key, {})
            cached       = cache_bucket.get(key)
            if cached and cached[0] > now:
                return self._clone_payload(cached[1])

            inflight_bucket = self._inflight.setdefault(bucket_key, {})
            inflight        = inflight_bucket.get(key)
            if inflight is None:
                inflight = asyncio.create_task(producer())
                inflight_bucket[key] = inflight
                is_owner = True
            else:
                is_owner = False

        try:
            payload = await inflight
        except Exception:
            if is_owner:
                async with self._lock:
                    if self._inflight.get(bucket_key, {}).get(key) is inflight:
                        self._inflight[bucket_key].pop(key, None)
            raise

        if is_owner:
            cached_payload = self._clone_payload(payload)
            async with self._lock:
                if self._inflight.get(bucket_key, {}).get(key) is inflight:
                    self._inflight[bucket_key].pop(key, None)
                cacheable = should_cache(payload) if callable(should_cache) else True
                if cacheable:
                    self._cache.setdefault(bucket_key, {})[key] = (monotonic() + ttl, cached_payload)
                    self._prune_bucket(bucket_key, monotonic(), max_entries)
            return self._clone_payload(cached_payload)

        return self._clone_payload(payload)

    @staticmethod
    def _clone_payload(payload):
        if isinstance(payload, list):
            return [MethodCache._clone_payload(item) for item in payload]
        if isinstance(payload, dict):
            return {key: MethodCache._clone_payload(value) for key, value in payload.items()}
        if hasattr(payload, "model_copy"):
            return payload.model_copy(deep=True)
        return deepcopy(payload)

    def _prune_bucket(self, bucket_key: tuple[str, str], now: float, max_entries: int):
        bucket = self._cache.get(bucket_key, {})

        expired = [k for k, (expires_at, _) in bucket.items() if expires_at <= now]
        for key in expired:
            bucket.pop(key, None)

        overflow = len(bucket) - max_entries
        if overflow > 0:
            oldest = sorted(bucket.items(), key=lambda kv: kv[1][0])[:overflow]
            for key, _ in oldest:
                bucket.pop(key, None)

        if not bucket:
            self._cache.pop(bucket_key, None)
            self._inflight.pop(bucket_key, None)


method_cache = MethodCache()
