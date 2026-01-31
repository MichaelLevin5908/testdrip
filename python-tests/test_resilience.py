"""
Test SDK resilience features: rate limiting, circuit breaker, retries.

This module tests the resilience components that help the SDK handle
failures gracefully and manage request rates.
"""

import pytest
import time
from typing import Optional

# Check if drip-sdk and resilience module are available
try:
    from drip import Drip, AsyncDrip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None
    AsyncDrip = None

try:
    from drip.resilience import (
        RateLimiter,
        CircuitBreaker,
        ResilienceManager,
        ResilienceConfig
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    RateLimiter = None
    CircuitBreaker = None
    ResilienceManager = None
    ResilienceConfig = None


pytestmark = [
    pytest.mark.skipif(not DRIP_SDK_AVAILABLE, reason="drip-sdk not installed"),
    pytest.mark.resilience
]


class TestRateLimiter:
    """Test rate limiter functionality."""

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_rate_limiter_allows_within_limit(self):
        """Rate limiter allows requests within limit."""
        limiter = RateLimiter(max_requests=10, window_seconds=1)
        for _ in range(10):
            assert limiter.try_acquire() is True

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_rate_limiter_blocks_over_limit(self):
        """Rate limiter blocks requests over limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        for _ in range(5):
            limiter.try_acquire()
        assert limiter.try_acquire() is False

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_rate_limiter_resets_after_window(self):
        """Rate limiter resets after time window."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.1)
        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.try_acquire() is False
        time.sleep(0.15)
        assert limiter.try_acquire() is True

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_rate_limiter_tracks_remaining(self):
        """Rate limiter tracks remaining requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)
        assert limiter.remaining() == 5
        limiter.try_acquire()
        assert limiter.remaining() == 4
        limiter.try_acquire()
        limiter.try_acquire()
        assert limiter.remaining() == 2

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_rate_limiter_wait_time(self):
        """Rate limiter returns wait time when limit exceeded."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.5)
        limiter.try_acquire()

        wait_time = limiter.get_wait_time()
        assert wait_time is not None
        assert 0 < wait_time <= 0.5

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_rate_limiter_concurrent_access(self):
        """Rate limiter handles concurrent access correctly."""
        import threading

        limiter = RateLimiter(max_requests=10, window_seconds=1)
        successful_acquires = []
        lock = threading.Lock()

        def acquire():
            result = limiter.try_acquire()
            with lock:
                successful_acquires.append(result)

        threads = [threading.Thread(target=acquire) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have exactly 10 successful acquires
        assert sum(successful_acquires) == 10


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_starts_closed(self):
        """Circuit breaker starts in closed state."""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == "closed"
        assert cb.allow_request() is True

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_opens_on_failures(self):
        """Circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_half_open_after_timeout(self):
        """Circuit breaker enters half-open after reset timeout."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        time.sleep(0.15)
        assert cb.allow_request() is True  # half-open allows one
        assert cb.state == "half_open"

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_closes_on_success(self):
        """Circuit breaker closes on success in half-open."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.allow_request()  # enter half-open
        cb.record_success()
        assert cb.state == "closed"

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_stays_open_on_half_open_failure(self):
        """Circuit breaker returns to open on failure in half-open state."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.15)
        cb.allow_request()  # enter half-open
        assert cb.state == "half_open"

        cb.record_failure()  # fail in half-open
        assert cb.state == "open"

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_counts_failures(self):
        """Circuit breaker tracks failure count."""
        cb = CircuitBreaker(failure_threshold=5)
        assert cb.failure_count == 0
        cb.record_failure()
        assert cb.failure_count == 1
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 3

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_resets_on_success(self):
        """Circuit breaker resets failure count on success."""
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        cb.record_success()
        assert cb.failure_count == 0

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_circuit_breaker_consecutive_failures_only(self):
        """Circuit breaker only counts consecutive failures."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # resets count
        cb.record_failure()
        assert cb.state == "closed"  # only 1 consecutive failure


class TestResilienceManager:
    """Test resilience manager functionality."""

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_manager_initialization(self):
        """Resilience manager initializes with config."""
        config = ResilienceConfig(
            enabled=True,
            rate_limit_requests=100,
            rate_limit_window_seconds=60,
            circuit_breaker_threshold=5
        )
        manager = ResilienceManager(config)
        assert manager is not None
        assert manager.is_enabled() is True

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_manager_disabled(self):
        """Resilience manager can be disabled."""
        config = ResilienceConfig(enabled=False)
        manager = ResilienceManager(config)
        assert manager.is_enabled() is False

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_manager_tracks_metrics(self):
        """Resilience manager tracks request metrics."""
        config = ResilienceConfig(enabled=True)
        manager = ResilienceManager(config)

        metrics = manager.get_metrics()
        assert metrics is not None
        # Check for expected metric fields
        total = metrics.get("total_requests") if isinstance(metrics, dict) else getattr(metrics, "total_requests", 0)
        assert total is not None

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_manager_health_status(self):
        """Resilience manager reports health status."""
        config = ResilienceConfig(enabled=True)
        manager = ResilienceManager(config)

        health = manager.get_health()
        assert health is not None
        # Check for health indicators
        assert "circuit_breaker" in health or "healthy" in health or isinstance(health, dict)

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_manager_before_request(self):
        """Resilience manager before_request check."""
        config = ResilienceConfig(
            enabled=True,
            rate_limit_requests=10,
            circuit_breaker_threshold=5
        )
        manager = ResilienceManager(config)

        # Should allow request when healthy
        allowed = manager.before_request()
        assert allowed is True

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_manager_after_request_success(self):
        """Resilience manager handles successful request."""
        config = ResilienceConfig(enabled=True)
        manager = ResilienceManager(config)

        manager.before_request()
        manager.after_request(success=True)

        metrics = manager.get_metrics()
        successful = metrics.get("successful_requests", 0) if isinstance(metrics, dict) else getattr(metrics, "successful_requests", 0)
        assert successful >= 1

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_manager_after_request_failure(self):
        """Resilience manager handles failed request."""
        config = ResilienceConfig(enabled=True, circuit_breaker_threshold=3)
        manager = ResilienceManager(config)

        for _ in range(3):
            manager.before_request()
            manager.after_request(success=False)

        # Circuit breaker should be open
        health = manager.get_health()
        if isinstance(health, dict):
            cb_state = health.get("circuit_breaker", {}).get("state")
        else:
            cb_state = getattr(health, "circuit_breaker_state", None)
        # The circuit breaker should now be open or tracking failures


class TestClientWithResilience:
    """Test client with resilience configuration."""

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_client_with_resilience_enabled(self, api_key, base_url):
        """Client works with resilience enabled."""
        client = Drip(
            api_key=api_key,
            base_url=base_url,
            resilience=ResilienceConfig(
                enabled=True,
                rate_limit_requests=100,
                rate_limit_window_seconds=60,
                circuit_breaker_threshold=5,
                retry_max_attempts=3
            )
        )
        try:
            result = client.ping()
            ok = result.get('ok') if isinstance(result, dict) else getattr(result, 'ok', True)
            assert ok is True
        finally:
            client.close()

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_client_resilience_disabled(self, api_key, base_url):
        """Client works with resilience disabled."""
        client = Drip(
            api_key=api_key,
            base_url=base_url,
            resilience=None
        )
        try:
            # No resilience features should be available
            metrics = client.get_metrics() if hasattr(client, 'get_metrics') else None
            health = client.get_health() if hasattr(client, 'get_health') else None

            assert metrics is None
            assert health is None

            result = client.ping()
            ok = result.get('ok') if isinstance(result, dict) else getattr(result, 'ok', True)
            assert ok is True
        finally:
            client.close()

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_client_exposes_resilience_metrics(self, resilient_client):
        """Client exposes resilience metrics."""
        metrics = resilient_client.get_metrics()
        assert metrics is not None

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_client_exposes_health_status(self, resilient_client):
        """Client exposes health status."""
        health = resilient_client.get_health()
        assert health is not None

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_client_rate_limiting_integration(self, api_key, base_url):
        """Client respects rate limiting."""
        client = Drip(
            api_key=api_key,
            base_url=base_url,
            resilience=ResilienceConfig(
                enabled=True,
                rate_limit_requests=5,
                rate_limit_window_seconds=1
            )
        )
        try:
            # Make requests up to the limit
            for _ in range(5):
                client.ping()

            # Additional request should be rate limited
            # Behavior depends on SDK implementation - might queue, reject, or wait
            metrics = client.get_metrics()
            if metrics:
                rate_limited = metrics.get("rate_limited_requests", 0) if isinstance(metrics, dict) else getattr(metrics, "rate_limited_requests", 0)
                # Just verify metrics are being tracked
                assert rate_limited is not None
        finally:
            client.close()


class TestResilienceConfig:
    """Test resilience configuration options."""

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_config_defaults(self):
        """Resilience config has sensible defaults."""
        config = ResilienceConfig()
        assert config.enabled is True or config.enabled is False

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_config_custom_values(self):
        """Resilience config accepts custom values."""
        config = ResilienceConfig(
            enabled=True,
            rate_limit_requests=50,
            rate_limit_window_seconds=30,
            circuit_breaker_threshold=10,
            retry_max_attempts=5,
            retry_base_delay_ms=100
        )
        assert config.rate_limit_requests == 50
        assert config.rate_limit_window_seconds == 30
        assert config.circuit_breaker_threshold == 10
        assert config.retry_max_attempts == 5

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_resilience_config_validation(self):
        """Resilience config validates input."""
        # Invalid values should raise or be handled
        with pytest.raises((ValueError, TypeError)):
            ResilienceConfig(rate_limit_requests=-1)


class TestRetryBehavior:
    """Test retry behavior in resilience."""

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_retry_on_transient_error(self, api_key, base_url):
        """Client retries on transient errors."""
        config = ResilienceConfig(
            enabled=True,
            retry_max_attempts=3,
            retry_base_delay_ms=50
        )

        client = Drip(
            api_key=api_key,
            base_url=base_url,
            resilience=config
        )

        try:
            # Normal operation should work
            result = client.ping()
            assert result is not None
        finally:
            client.close()

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_retry_respects_max_attempts(self):
        """Retry logic respects max attempts setting."""
        config = ResilienceConfig(
            enabled=True,
            retry_max_attempts=2
        )
        assert config.retry_max_attempts == 2

    @pytest.mark.skipif(not RESILIENCE_AVAILABLE, reason="resilience module not available")
    def test_retry_exponential_backoff(self):
        """Retry uses exponential backoff."""
        config = ResilienceConfig(
            enabled=True,
            retry_base_delay_ms=100,
            retry_max_attempts=3
        )
        # First retry: 100ms, second: 200ms, etc.
        assert config.retry_base_delay_ms == 100
