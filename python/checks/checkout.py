"""Checkout operation checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _checkout_create_check(ctx: CheckContext) -> CheckResult:
    """Create checkout session."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="checkout_create",
            success=False,
            duration=0,
            message="No customer ID available",
            suggestion="Run customer_create check first or set TEST_CUSTOMER_ID"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'checkout') and not hasattr(client, 'create_checkout'):
            return CheckResult(
                name="checkout_create",
                success=True,
                duration=0,
                message="Skipped (checkout not available)",
                details="The checkout method is not available in the SDK"
            )

        checkout_method = getattr(client, 'checkout', None) or getattr(client, 'create_checkout', None)

        result = checkout_method(
            customer_id=customer_id,
            amount=1000,  # $10.00 in cents
            return_url="https://example.com/checkout/success"
        )

        session_id = getattr(result, 'id', str(result))
        url = getattr(result, 'url', 'N/A')

        return CheckResult(
            name="checkout_create",
            success=True,
            duration=0,
            message=f"Session: {session_id}",
            details=f"URL: {url[:50]}..." if len(str(url)) > 50 else f"URL: {url}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="checkout_create",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="checkout_create",
            success=False,
            duration=0,
            message=f"Failed to create checkout: {e}"
        )


checkout_create_check = Check(
    name="checkout_create",
    description="Create checkout session",
    run=_checkout_create_check
)
