"""SDK wrapper matching TypeScript version."""
from typing import Optional, Any, Callable
import uuid

# Import from drip-sdk package
try:
    from drip import Drip as DripSDK
    from drip import DripAuthenticationError
except ImportError:
    # Fallback if package structure is different
    try:
        from drip_sdk import Drip as DripSDK
        from drip_sdk import DripAuthenticationError
    except ImportError:
        DripSDK = None
        DripAuthenticationError = Exception


def create_client(api_key: str, base_url: str) -> Any:
    """Create a Drip SDK client instance.

    Args:
        api_key: The Drip API key
        base_url: The API base URL

    Returns:
        Configured Drip client instance
    """
    if DripSDK is None:
        raise ImportError(
            "drip-sdk package is not installed. "
            "Install it with: pip install drip-sdk"
        )

    # Remove /v1 suffix if present, SDK may add it
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/v1"):
        clean_url = clean_url[:-3]

    return DripSDK(api_key=api_key, base_url=clean_url)


def generate_idempotency_key(prefix: str = "health_check") -> str:
    """Generate a unique idempotency key.

    Args:
        prefix: Prefix for the key

    Returns:
        Unique idempotency key string
    """
    return f"{prefix}_{uuid.uuid4().hex}"


def generate_external_id(prefix: str = "health_check") -> str:
    """Generate a unique external ID for test resources.

    Args:
        prefix: Prefix for the ID

    Returns:
        Unique external ID string
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
