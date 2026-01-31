"""Idempotency check."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client, generate_idempotency_key


async def _idempotency_check(ctx: CheckContext) -> CheckResult:
    """Verify idempotent charge handling."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="idempotency",
            success=False,
            duration=0,
            message="No customer ID available"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)
        idempotency_key = generate_idempotency_key("idem_test")

        # First charge
        result1 = client.charge(
            customer_id=customer_id,
            meter="api_calls",
            quantity=1,
            idempotency_key=idempotency_key
        )

        # Second charge with same key
        result2 = client.charge(
            customer_id=customer_id,
            meter="api_calls",
            quantity=1,
            idempotency_key=idempotency_key
        )

        # Get charge IDs
        if hasattr(result1, 'charge'):
            charge_id_1 = result1.charge.id
            charge_id_2 = result2.charge.id
            is_replay = getattr(result2, 'is_replay', False)
        else:
            charge_id_1 = getattr(result1, 'id', str(result1))
            charge_id_2 = getattr(result2, 'id', str(result2))
            is_replay = getattr(result2, 'is_replay', charge_id_1 == charge_id_2)

        # Verify replay detection
        if is_replay or charge_id_1 == charge_id_2:
            return CheckResult(
                name="idempotency",
                success=True,
                duration=0,
                message="Idempotency working correctly",
                details=f"Replay detected, same charge ID: {charge_id_1}"
            )
        else:
            return CheckResult(
                name="idempotency",
                success=False,
                duration=0,
                message="Idempotency not working",
                suggestion="Second request should be marked as replay"
            )
    except Exception as e:
        return CheckResult(
            name="idempotency",
            success=False,
            duration=0,
            message=f"Idempotency check failed: {e}"
        )


idempotency_check = Check(
    name="idempotency",
    description="Verify idempotent charge handling",
    run=_idempotency_check
)
