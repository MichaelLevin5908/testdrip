"""Pytest fixtures for Drip SDK tests.

This module provides shared fixtures used across all test modules.
Fixtures handle client creation, test data setup, and cleanup.
"""
import os
import uuid
import pytest
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try to import Drip SDK - tests will skip if not available
try:
    from drip import Drip, AsyncDrip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None
    AsyncDrip = None


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "quick: mark test as quick smoke test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture(scope="session")
def api_key():
    """Get API key from environment.

    Returns:
        str: The Drip API key

    Raises:
        pytest.skip: If DRIP_API_KEY is not set
    """
    key = os.getenv("DRIP_API_KEY")
    if not key:
        pytest.skip("DRIP_API_KEY not set in environment")
    return key


@pytest.fixture(scope="session")
def base_url():
    """Get API URL from environment.

    Returns:
        str: The Drip API base URL (defaults to https://api.drip.re)
    """
    return os.getenv("DRIP_API_URL", "https://api.drip.re")


@pytest.fixture(scope="session")
def check_sdk():
    """Verify SDK is installed.

    Raises:
        pytest.skip: If drip-sdk is not installed
    """
    if not DRIP_SDK_AVAILABLE:
        pytest.skip("drip-sdk not installed - run 'pip install drip-sdk'")


@pytest.fixture(scope="session")
def client(api_key, base_url, check_sdk):
    """Create a synchronous Drip client for the test session.

    Args:
        api_key: The API key fixture
        base_url: The base URL fixture
        check_sdk: Fixture to verify SDK is available

    Returns:
        Drip: A configured Drip client instance
    """
    client = Drip(api_key=api_key, base_url=base_url)
    yield client
    # Cleanup: close the client if it has a close method
    if hasattr(client, 'close'):
        try:
            client.close()
        except Exception:
            pass


@pytest.fixture(scope="session")
def async_client_factory(api_key, base_url, check_sdk):
    """Factory fixture to create AsyncDrip clients.

    This returns a factory function rather than a client instance,
    allowing tests to create fresh async clients as needed.

    Args:
        api_key: The API key fixture
        base_url: The base URL fixture
        check_sdk: Fixture to verify SDK is available

    Returns:
        callable: A function that creates AsyncDrip instances
    """
    def _create_client():
        return AsyncDrip(api_key=api_key, base_url=base_url)
    return _create_client


@pytest.fixture(scope="session")
def test_customer_id():
    """Generate a unique test customer external ID.

    Returns:
        str: A unique external customer ID for testing
    """
    return f"sdk_test_{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="session")
def test_onchain_address():
    """Provide a test blockchain address.

    Returns:
        str: A valid Ethereum address format for testing
    """
    # Using a deterministic test address (not a real funded address)
    return "0x742d35Cc6634C0532925a3b844Bc9e7595f00000"


@pytest.fixture(scope="session")
def test_customer(client, test_customer_id, test_onchain_address):
    """Create a test customer for the session.

    This fixture creates a customer that can be reused across all tests
    in the session to avoid creating too many test customers.

    Args:
        client: The Drip client fixture
        test_customer_id: Unique external customer ID
        test_onchain_address: Test blockchain address

    Returns:
        Customer: The created customer object
    """
    try:
        customer = client.create_customer(
            onchain_address=test_onchain_address,
            external_customer_id=test_customer_id,
            metadata={
                "test": True,
                "suite": "python_sdk_tests",
                "session_id": uuid.uuid4().hex[:8]
            }
        )
        return customer
    except Exception as e:
        pytest.skip(f"Failed to create test customer: {e}")


@pytest.fixture(scope="session")
def test_workflow_slug():
    """Generate a unique test workflow slug.

    Returns:
        str: A unique workflow slug for testing
    """
    return f"sdk-test-workflow-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_workflow(client, test_workflow_slug):
    """Create a test workflow for the session.

    Args:
        client: The Drip client fixture
        test_workflow_slug: Unique workflow slug

    Returns:
        Workflow: The created workflow object
    """
    try:
        workflow = client.create_workflow(
            name="SDK Test Workflow",
            slug=test_workflow_slug,
            product_surface="AGENT",
            description="Automated test workflow for Python SDK tests"
        )
        return workflow
    except Exception as e:
        # Workflow creation might fail if feature not available
        pytest.skip(f"Failed to create test workflow: {e}")


@pytest.fixture(scope="session")
def test_webhook_url():
    """Provide a test webhook URL.

    Returns:
        str: A webhook URL for testing (not a real endpoint)
    """
    return f"https://webhook.site/test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_id():
    """Generate a unique ID for each test.

    This fixture provides a fresh UUID for each test that needs
    unique identifiers for idempotency keys, external IDs, etc.

    Returns:
        str: A unique hex string
    """
    return uuid.uuid4().hex


@pytest.fixture
def idempotency_key(unique_id):
    """Generate a unique idempotency key.

    Args:
        unique_id: The unique ID fixture

    Returns:
        str: An idempotency key for testing
    """
    return f"idem_test_{unique_id}"


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session.

    This overrides the default pytest-asyncio event loop fixture
    to provide a session-scoped event loop for all async tests.

    Returns:
        asyncio.AbstractEventLoop: The event loop
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# Cleanup tracking for created resources
@pytest.fixture(scope="session")
def cleanup_tracker():
    """Track resources created during tests for cleanup.

    Returns:
        dict: A dictionary to track created resources
    """
    return {
        "customers": [],
        "webhooks": [],
        "workflows": [],
        "runs": []
    }


@pytest.fixture(scope="session", autouse=True)
def cleanup_resources(client, cleanup_tracker):
    """Clean up resources after all tests complete.

    This fixture runs automatically after all tests and attempts
    to clean up any resources that were created during testing.
    """
    yield  # Run all tests first

    # Cleanup webhooks
    for webhook_id in cleanup_tracker.get("webhooks", []):
        try:
            client.delete_webhook(webhook_id)
        except Exception:
            pass  # Ignore cleanup errors

    # Note: Customers and workflows typically shouldn't be deleted
    # as they may be needed for audit trails


# Utility functions available to tests
def generate_test_address():
    """Generate a random test Ethereum address.

    Returns:
        str: A randomly generated Ethereum address
    """
    random_hex = uuid.uuid4().hex + uuid.uuid4().hex[:8]
    return f"0x{random_hex}"


def generate_correlation_id():
    """Generate a correlation ID for tracing.

    Returns:
        str: A correlation ID string
    """
    return f"trace_{uuid.uuid4().hex[:16]}"
