"""Configuration loading matching TypeScript version."""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration."""
    api_key: str
    api_url: str
    test_customer_id: Optional[str] = None
    skip_cleanup: bool = False
    timeout: int = 30000  # milliseconds


def load_config(environment: Optional[str] = None) -> Config:
    """Load configuration from environment variables.

    Args:
        environment: Optional environment override (not currently used)

    Returns:
        Config object with loaded values

    Raises:
        ValueError: If required DRIP_API_KEY is not set
    """
    api_key = os.getenv("DRIP_API_KEY")
    if not api_key:
        raise ValueError(
            "DRIP_API_KEY environment variable is required. "
            "Set it in your .env file or environment."
        )

    api_url = os.getenv("DRIP_API_URL", "https://api.drip.re")

    # Normalize URL - ensure /v1 suffix
    if not api_url.endswith("/v1"):
        api_url = api_url.rstrip("/") + "/v1"

    test_customer_id = os.getenv("TEST_CUSTOMER_ID")
    skip_cleanup = os.getenv("SKIP_CLEANUP", "").lower() in ("true", "1", "yes")
    timeout = int(os.getenv("CHECK_TIMEOUT", "30000"))

    return Config(
        api_key=api_key,
        api_url=api_url,
        test_customer_id=test_customer_id,
        skip_cleanup=skip_cleanup,
        timeout=timeout
    )
