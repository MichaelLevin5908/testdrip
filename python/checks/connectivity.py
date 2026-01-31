"""Connectivity and authentication checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _connectivity_check(ctx: CheckContext) -> CheckResult:
    """Verify SDK can reach the API."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        # Try to ping or make a basic request
        if hasattr(client, 'ping'):
            result = client.ping()
            return CheckResult(
                name="connectivity",
                success=True,
                duration=0,
                message="API is reachable",
                details=f"Response: {result}"
            )
        else:
            # Fallback: try listing customers with limit 1
            client.list_customers(limit=1)
            return CheckResult(
                name="connectivity",
                success=True,
                duration=0,
                message="API is reachable",
                details="Connected via list_customers"
            )
    except Exception as e:
        return CheckResult(
            name="connectivity",
            success=False,
            duration=0,
            message=f"Cannot reach API: {e}",
            suggestion="Check DRIP_API_URL and network connectivity"
        )


connectivity_check = Check(
    name="connectivity",
    description="Verify API connectivity",
    run=_connectivity_check,
    quick=True
)


async def _authentication_check(ctx: CheckContext) -> CheckResult:
    """Verify API key is valid."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)
        # Make an authenticated request
        client.list_customers(limit=1)
        return CheckResult(
            name="authentication",
            success=True,
            duration=0,
            message="API key is valid"
        )
    except Exception as e:
        error_str = str(e).lower()
        if "authentication" in error_str or "unauthorized" in error_str or "401" in error_str:
            return CheckResult(
                name="authentication",
                success=False,
                duration=0,
                message="Invalid API key",
                suggestion="Check DRIP_API_KEY environment variable"
            )
        return CheckResult(
            name="authentication",
            success=False,
            duration=0,
            message=f"Authentication check failed: {e}"
        )


authentication_check = Check(
    name="authentication",
    description="Verify API key authentication",
    run=_authentication_check,
    quick=True
)
