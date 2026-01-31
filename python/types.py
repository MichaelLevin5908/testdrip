"""Type definitions matching TypeScript version."""
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Any


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    success: bool
    duration: float  # milliseconds
    message: str
    details: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class CheckContext:
    """Shared context passed to all checks."""
    api_key: str
    api_url: str
    test_customer_id: Optional[str] = None
    created_customer_id: Optional[str] = None
    skip_cleanup: bool = False
    timeout: int = 30000  # milliseconds
    # Dynamic fields set during checks
    created_charge_id: Optional[str] = None
    stream_meter: Any = None
    webhook_id: Optional[str] = None
    webhook_secret: Optional[str] = None
    run_id: Optional[str] = None


# Type alias for check functions
CheckFunction = Callable[[CheckContext], Awaitable[CheckResult]]


@dataclass
class Check:
    """Health check definition."""
    name: str
    description: str
    run: CheckFunction
    quick: bool = False
