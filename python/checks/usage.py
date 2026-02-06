"""Usage tracking check."""
import time
import uuid
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


async def _track_usage_idempotency_check(ctx: CheckContext) -> CheckResult:
    """Verify idempotency key deduplication in track_usage."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="track_usage_idempotency",
            success=False,
            duration=0,
            message="No customer ID available"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'track_usage'):
            return CheckResult(
                name="track_usage_idempotency",
                success=True,
                duration=0,
                message="Usage tracking not available in SDK",
                details="Skipping idempotency test"
            )

        idempotency_key = f"health-check-usage-idem-{int(time.time())}-{uuid.uuid4().hex[:8]}"

        # First call with idempotency key
        result1 = client.track_usage(
            customer_id=customer_id,
            meter="api_calls",
            quantity=5,
            units="requests",
            description="Idempotency test usage",
            idempotency_key=idempotency_key,
        )

        # Second call with same idempotency key - should return same event
        result2 = client.track_usage(
            customer_id=customer_id,
            meter="api_calls",
            quantity=5,
            units="requests",
            description="Idempotency test usage",
            idempotency_key=idempotency_key,
        )

        event_id_1 = getattr(result1, 'usage_event_id', str(result1))
        event_id_2 = getattr(result2, 'usage_event_id', str(result2))

        if event_id_1 == event_id_2:
            return CheckResult(
                name="track_usage_idempotency",
                success=True,
                duration=0,
                message="Duplicate prevented (same event ID)",
                details=f"Key: {idempotency_key}, Event ID: {event_id_1}"
            )
        else:
            return CheckResult(
                name="track_usage_idempotency",
                success=False,
                duration=0,
                message="Duplicate usage created",
                suggestion=f"First: {event_id_1}, Second: {event_id_2}"
            )
    except Exception as e:
        return CheckResult(
            name="track_usage_idempotency",
            success=False,
            duration=0,
            message=f"Idempotency check failed: {e}"
        )


track_usage_idempotency_check = Check(
    name="track_usage_idempotency",
    description="Verify idempotency key deduplication in track_usage",
    run=_track_usage_idempotency_check
)
