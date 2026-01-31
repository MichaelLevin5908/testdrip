"""Balance check."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _balance_get_check(ctx: CheckContext) -> CheckResult:
    """Get customer balance."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="balance_get",
            success=False,
            duration=0,
            message="No customer ID available",
            suggestion="Run customer_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)
        balance = client.get_balance(customer_id)

        # Handle different response formats
        balance_usdc = getattr(balance, 'balance_usdc', getattr(balance, 'balance', 'N/A'))
        available_usdc = getattr(balance, 'available_usdc', getattr(balance, 'available', balance_usdc))

        return CheckResult(
            name="balance_get",
            success=True,
            duration=0,
            message=f"Balance: {balance_usdc} USDC",
            details=f"available: {available_usdc} USDC"
        )
    except Exception as e:
        return CheckResult(
            name="balance_get",
            success=False,
            duration=0,
            message=f"Failed to get balance: {e}"
        )


balance_get_check = Check(
    name="balance_get",
    description="Get customer balance",
    run=_balance_get_check
)
