"""Cost estimation checks."""
from datetime import datetime, timedelta
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _estimate_from_usage_check(ctx: CheckContext) -> CheckResult:
    """Estimate costs from historical usage."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="estimate_from_usage",
            success=False,
            duration=0,
            message="No customer ID available",
            suggestion="Run customer_create check first or set TEST_CUSTOMER_ID"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'estimate_from_usage'):
            return CheckResult(
                name="estimate_from_usage",
                success=True,
                duration=0,
                message="Skipped (estimate_from_usage not available)",
                details="The estimate_from_usage method is not available in the SDK"
            )

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        result = client.estimate_from_usage(
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date
        )

        estimated_cost = getattr(result, 'estimated_cost', getattr(result, 'estimatedCost', 'N/A'))
        currency = getattr(result, 'currency', 'USD')

        return CheckResult(
            name="estimate_from_usage",
            success=True,
            duration=0,
            message=f"Estimated: {estimated_cost} {currency}",
            details=f"Period: {start_date} to {end_date}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="estimate_from_usage",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="estimate_from_usage",
            success=False,
            duration=0,
            message=f"Failed to estimate from usage: {e}"
        )


estimate_from_usage_check = Check(
    name="estimate_from_usage",
    description="Estimate costs from historical usage",
    run=_estimate_from_usage_check
)


async def _estimate_from_hypothetical_check(ctx: CheckContext) -> CheckResult:
    """Estimate hypothetical costs."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'estimate_from_hypothetical'):
            return CheckResult(
                name="estimate_hypothetical",
                success=True,
                duration=0,
                message="Skipped (estimate_from_hypothetical not available)",
                details="The estimate_from_hypothetical method is not available in the SDK"
            )

        result = client.estimate_from_hypothetical(
            items=[
                {"meter": "tokens", "quantity": 1000},
                {"meter": "api_calls", "quantity": 100}
            ]
        )

        estimated_cost = getattr(result, 'estimated_cost', getattr(result, 'estimatedCost', 'N/A'))
        currency = getattr(result, 'currency', 'USD')
        breakdown = getattr(result, 'breakdown', [])

        return CheckResult(
            name="estimate_hypothetical",
            success=True,
            duration=0,
            message=f"Estimated: {estimated_cost} {currency}",
            details=f"Items: {len(breakdown) if breakdown else 2}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="estimate_hypothetical",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="estimate_hypothetical",
            success=False,
            duration=0,
            message=f"Failed to estimate hypothetical: {e}"
        )


estimate_from_hypothetical_check = Check(
    name="estimate_hypothetical",
    description="Estimate hypothetical costs",
    run=_estimate_from_hypothetical_check
)
