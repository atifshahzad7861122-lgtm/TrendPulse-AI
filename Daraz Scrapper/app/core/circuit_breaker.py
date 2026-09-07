"""Circuit Breaker implementation for preventing cascading failures to upstream endpoints."""

import asyncio
import time
from typing import Any, Callable, Coroutine, Optional, TypeVar
from app.core.constants import CircuitState
from app.core.exceptions import CircuitBreakerOpenError
from app.core.logging import logger

T = TypeVar("T")


class CircuitBreaker:
    """Async-safe Circuit Breaker pattern with Closed, Open, and Half-Open states."""

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_state_change: float = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def success_count(self) -> int:
        return self._success_count

    async def can_execute(self) -> bool:
        """Check if execution is permitted based on circuit state and timeouts."""
        async with self._lock:
            now = time.monotonic()
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if (now - self._last_state_change) >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._last_state_change = now
                    self._success_count = 0
                    logger.info(
                        f"Circuit breaker '{self.name}' transitioning from OPEN to HALF_OPEN",
                        extra={"event": "circuit_half_open", "circuit_name": self.name},
                    )
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                return True

            return False

    async def record_success(self) -> None:
        """Record a successful operation and handle transition to CLOSED if in HALF_OPEN."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._last_state_change = time.monotonic()
                    logger.info(
                        f"Circuit breaker '{self.name}' successfully reset to CLOSED",
                        extra={"event": "circuit_closed", "circuit_name": self.name},
                    )
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record an operation failure and trip to OPEN if threshold reached."""
        async with self._lock:
            now = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_state_change = now
                self._failure_count += 1
                logger.warning(
                    f"Circuit breaker '{self.name}' tripped back to OPEN from HALF_OPEN due to: {error}",
                    extra={"event": "circuit_opened", "circuit_name": self.name, "error": str(error)},
                )
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_state_change = now
                    logger.warning(
                        f"Circuit breaker '{self.name}' tripped to OPEN (failures: {self._failure_count}/{self.failure_threshold})",
                        extra={"event": "circuit_opened", "circuit_name": self.name, "error": str(error)},
                    )

    async def execute(self, func: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
        """Execute async callable through the circuit breaker protection."""
        if not await self.can_execute():
            remaining = max(0.0, self.recovery_timeout - (time.monotonic() - self._last_state_change))
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. Requests blocked for {remaining:.1f}s",
                reset_timeout=remaining,
            )

        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as exc:
            await self.record_failure(exc)
            raise

    async def reset(self) -> None:
        """Manually reset the circuit breaker back to CLOSED state."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_state_change = time.monotonic()
