"""Usage tracking check."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _track_usage_check(ctx: CheckContext) -> CheckResult:
    """Track usage without charging."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="track_usage",
            success=False,
            duration=0,
            message="No customer ID available"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'track_usage'):
            return CheckResult(
                name="track_usage",
                success=True,
                duration=0,
                message="Usage tracking not available in SDK",
                details="Skipping usage tracking test"
            )

        result = client.track_usage(
            customer_id=customer_id,
            meter="tokens",
            quantity=500,
            units="tokens",
            description="Health check usage tracking"
        )

        return CheckResult(
            name="track_usage",
            success=True,
            duration=0,
            message="Usage tracked successfully",
            details="quantity: 500 tokens"
        )
    except Exception as e:
        return CheckResult(
            name="track_usage",
            success=False,
            duration=0,
            message=f"Usage tracking failed: {e}"
        )


track_usage_check = Check(
    name="track_usage",
    description="Track usage without charging",
    run=_track_usage_check
)
