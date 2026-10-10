"""Rate limiting & anti-flood middleware (Section 26). Registered before all handlers."""
from __future__ import annotations

from typing import Any
import time


from loguru import logger


class TokenBucket:
    """Simple in-memory token bucket."""

    def __init__(self, capacity: int, period: float) -> None:
        self.capacity = max(1, int(capacity))
        self.period = max(1.0, float(period))
        self._hits: dict[Any, list[float]] = {}

    def allow(self, key) -> tuple[bool, int]:
        now = time.monotonic()
        hits = [t for t in self._hits.get(key, []) if now - t < self.period]
        if len(hits) >= self.capacity:
            self._hits[key] = hits
            retry = int(self.period - (now - hits[0])) + 1
            return False, max(1, retry)
        hits.append(now)
        self._hits[key] = hits
        return True, 0

    def prune(self) -> None:
        now = time.monotonic()
        for key in list(self._hits.keys()):
            self._hits[key] = [t for t in self._hits[key] if now - t < self.period]
            if not self._hits[key]:
                del self._hits[key]


class RateLimiter:
    """Per-user and per-chat token buckets + FloodWait backoff (Section 26).

    Registered BEFORE all handlers: when a limit is exceeded the update is
    not processed further and the user gets a localized 'slow down' reply.
    """

    def __init__(self, adapter, t_func=None) -> None:
        self.adapter = adapter
        self.t = t_func
        self.user_bucket = TokenBucket(10, 10)
        self.chat_bucket = TokenBucket(60, 60)
        self._trigger_buckets: dict[str, TokenBucket] = {}
        self._flood_until: float = 0.0
        self._flood_hits: int = 0
        self._last_prune: float = time.monotonic()

    async def allow(self, ctx) -> bool:
        """Return True when the update may be processed; reply + False otherwise."""
        now = time.monotonic()
        if now - self._last_prune > 300:
            self.user_bucket.prune()
            self.chat_bucket.prune()
            self._last_prune = now
        if now < self._flood_until:
            wait = int(self._flood_until - now)
            await self._slow_down(ctx, wait)
            return False
        ok, retry = self.user_bucket.allow(ctx.user_id)
        if not ok:
            await self._slow_down(ctx, retry)
            return False
        ok, retry = self.chat_bucket.allow(ctx.chat_id)
        if not ok:
            await self._slow_down(ctx, retry)
            return False
        return True

    async def allow_trigger(self, trigger: dict, ctx) -> bool:
        """Per-trigger token-bucket override (trigger.rate_count / rate_per)."""
        count = int(trigger.get("rate_count") or 0)
        if count <= 0:
            return True
        period = float(trigger.get("rate_per") or 10)
        key = "trg:" + str(trigger.get("id", ""))
        bucket = self._trigger_buckets.get(key)
        if bucket is None or bucket.capacity != count or bucket.period != period:
            bucket = TokenBucket(count, period)
            self._trigger_buckets[key] = bucket
        ok, retry = bucket.allow(ctx.user_id)
        if not ok:
            await self._slow_down(ctx, retry)
            return False
        return True

    async def note_flood_wait(self, seconds: float) -> None:
        """Exponential backoff after a Telegram FloodWaitError."""
        self._flood_hits += 1
        backoff = max(float(seconds), 1.0) * (2 ** min(self._flood_hits - 1, 4))
        self._flood_until = time.monotonic() + backoff
        logger.warning("FloodWait: backing off for {:.1f}s (hit #{})", backoff, self._flood_hits)

    def reset_flood(self) -> None:
        self._flood_hits = 0
        self._flood_until = 0.0

    async def _slow_down(self, ctx, retry: int) -> None:
        text = f"⏳ Slow down, please try again in {retry}s."
        if self.t is not None:
            text = self.t(getattr(ctx, "language", "en") or "en", "rate_limit.slow_down",
                retry=retry) or text
        try:
            await self.adapter.send_text(ctx, text)
        except Exception:
            logger.exception("failed to send the rate-limit reply")
