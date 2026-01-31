"""
Pytest configuration and fixtures for Drip SDK tests.

This module provides shared fixtures and configuration for testing
the Drip Python SDK functionality.
"""

import os
import sys
import uuid
import asyncio
import pytest
from typing import Generator, AsyncGenerator, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if drip-sdk is available
try:
    from drip import Drip, AsyncDrip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None
    AsyncDrip = None

# Try importing resilience components
try:
    from drip.resilience import ResilienceConfig
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    ResilienceConfig = None


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "quick: marks test as quick smoke test")
    config.addinivalue_line("markers", "slow: marks test as slow running")
    config.addinivalue_line("markers", "asyncio: marks test as async")
    config.addinivalue_line("markers", "resilience: marks test requiring resilience module")
    config.addinivalue_line("markers", "middleware: marks test requiring middleware module")
    config.addinivalue_line("markers", "langchain: marks test requiring langchain integration")


def generate_test_address() -> str:
    """Generate a random Ethereum-like address for testing."""
    return "0x" + uuid.uuid4().hex[:40]


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return f"test-{uuid.uuid4().hex[:12]}"


# Session-scoped fixtures

@pytest.fixture(scope="session")
def api_key() -> str:
    """Get API key from environment."""
    key = os.getenv("DRIP_API_KEY")
    if not key:
        pytest.skip("DRIP_API_KEY not set")
    return key


@pytest.fixture(scope="session")
def base_url() -> str:
    """Get base URL from environment or use default."""
    return os.getenv("DRIP_API_URL", "https://api.drip.re")


@pytest.fixture(scope="session")
def check_sdk():
    """Verify drip-sdk is installed."""
    if not DRIP_SDK_AVAILABLE:
        pytest.skip("drip-sdk not installed")
    return True


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def client(api_key, base_url, check_sdk) -> Generator:
    """Create a synchronous Drip client for testing."""
    client = Drip(api_key=api_key, base_url=base_url)
    yield client
    client.close()


@pytest.fixture(scope="session")
def async_client(api_key, base_url, check_sdk, event_loop) -> Generator:
    """Create an async Drip client for testing."""
    async def create():
        return AsyncDrip(api_key=api_key, base_url=base_url)

    async def close(client):
        await client.close()

    client = event_loop.run_until_complete(create())
    yield client
    event_loop.run_until_complete(close(client))


@pytest.fixture
def async_client_factory(api_key, base_url, check_sdk):
    """Factory function for creating AsyncDrip instances."""
    clients = []

    def factory():
        client = AsyncDrip(api_key=api_key, base_url=base_url)
        clients.append(client)
        return client

    yield factory

    # Cleanup all created clients
    async def cleanup():
        for client in clients:
            try:
                await client.close()
            except Exception:
                pass

    loop = asyncio.get_event_loop()
    loop.run_until_complete(cleanup())


@pytest.fixture(scope="session")
def resilient_client(api_key, base_url, check_sdk) -> Generator:
    """Create a client with resilience enabled."""
    if not RESILIENCE_AVAILABLE:
        pytest.skip("Resilience module not available")

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
    yield client
    client.close()


@pytest.fixture(scope="session")
def test_customer_id() -> str:
    """Generate a unique test customer external ID."""
    return f"test-customer-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_onchain_address() -> str:
    """Provide a test blockchain address."""
    return generate_test_address()


@pytest.fixture(scope="session")
def test_customer(client, test_customer_id, test_onchain_address):
    """Create a session-level test customer."""
    customer = client.create_customer(
        external_id=test_customer_id,
        name="Test Customer",
        email=f"test-{test_customer_id}@example.com",
        onchain_address=test_onchain_address,
        metadata={"test": True, "created_by": "pytest"}
    )
    yield customer
    # Note: Customer cleanup is typically not needed as test customers
    # can be reused or will be cleaned up separately


@pytest.fixture(scope="session")
def test_workflow_slug() -> str:
    """Generate a unique workflow slug."""
    return f"test-workflow-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_workflow(client, test_workflow_slug):
    """Create a session-level test workflow."""
    workflow = client.create_workflow(
        name=f"Test Workflow {test_workflow_slug}",
        slug=test_workflow_slug,
        description="Automated test workflow"
    )
    yield workflow


@pytest.fixture(scope="session")
def test_webhook_url() -> str:
    """Provide a test webhook URL."""
    # Use a test webhook service URL
    return os.getenv("TEST_WEBHOOK_URL", "https://webhook.site/test-drip-sdk")


@pytest.fixture(scope="session")
def cleanup_tracker():
    """Track resources for cleanup after tests."""
    resources = {
        "webhooks": [],
        "workflows": [],
        "customers": []
    }
    yield resources


# Function-scoped fixtures

@pytest.fixture
def unique_id() -> str:
    """Generate a unique ID for each test."""
    return uuid.uuid4().hex[:12]


@pytest.fixture
def idempotency_key() -> str:
    """Generate a unique idempotency key for each test."""
    return f"idem-{uuid.uuid4().hex}"


@pytest.fixture
def correlation_id() -> str:
    """Generate a correlation ID for request tracing."""
    return generate_correlation_id()


# Async-specific fixtures

@pytest.fixture
async def async_test_customer(async_client, unique_id):
    """Create a test customer using async client."""
    customer = await async_client.create_customer(
        external_id=f"async-test-{unique_id}",
        name="Async Test Customer",
        email=f"async-test-{unique_id}@example.com",
        metadata={"async_test": True}
    )
    yield customer


@pytest.fixture
async def async_test_workflow(async_client, unique_id):
    """Create a test workflow using async client."""
    workflow = await async_client.create_workflow(
        name=f"Async Test Workflow {unique_id}",
        slug=f"async-workflow-{unique_id}",
        description="Automated async test workflow"
    )
    yield workflow


# Skip markers for conditional tests

pytestmark_sdk = pytest.mark.skipif(
    not DRIP_SDK_AVAILABLE,
    reason="drip-sdk not installed"
)

pytestmark_resilience = pytest.mark.skipif(
    not RESILIENCE_AVAILABLE,
    reason="resilience module not available"
)
