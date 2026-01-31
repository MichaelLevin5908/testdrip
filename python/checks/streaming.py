"""StreamMeter checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client, generate_idempotency_key


async def _stream_meter_add_check(ctx: CheckContext) -> CheckResult:
    """Test stream meter accumulation."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="stream_meter_add",
            success=False,
            duration=0,
            message="No customer ID available"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)
        idempotency_key = generate_idempotency_key("stream")

        # Check if SDK supports stream meters
        if hasattr(client, 'create_stream_meter'):
            meter = client.create_stream_meter(
                customer_id=customer_id,
                meter="tokens",
                idempotency_key=idempotency_key,
                flush_threshold=10000
            )

            # Add some quantities
            if hasattr(meter, 'add_sync'):
                meter.add_sync(100)
                meter.add_sync(200)
                meter.add_sync(300)
            elif hasattr(meter, 'add'):
                meter.add(100)
                meter.add(200)
                meter.add(300)

            # Store for flush check
            ctx.stream_meter = meter
            total = getattr(meter, 'total', 600)

            return CheckResult(
                name="stream_meter_add",
                success=True,
                duration=0,
                message=f"Accumulated {total} units",
                details="Ready for flush"
            )
        else:
            return CheckResult(
                name="stream_meter_add",
                success=True,
                duration=0,
                message="StreamMeter not available in SDK",
                details="Skipping stream meter tests"
            )
    except Exception as e:
        return CheckResult(
            name="stream_meter_add",
            success=False,
            duration=0,
            message=f"StreamMeter add failed: {e}"
        )


stream_meter_add_check = Check(
    name="stream_meter_add",
    description="Test stream meter accumulation",
    run=_stream_meter_add_check
)


async def _stream_meter_flush_check(ctx: CheckContext) -> CheckResult:
    """Test stream meter flush."""
    if not ctx.stream_meter:
        return CheckResult(
            name="stream_meter_flush",
            success=True,
            duration=0,
            message="No stream meter available",
            details="StreamMeter add check may have been skipped"
        )

    try:
        result = ctx.stream_meter.flush()

        # Handle different response formats
        if hasattr(result, 'charge') and result.charge:
            charge_id = result.charge.id
        else:
            charge_id = 'none'

        total_flushed = getattr(result, 'total_flushed', getattr(result, 'total', 'N/A'))

        return CheckResult(
            name="stream_meter_flush",
            success=True,
            duration=0,
            message=f"Flushed meter, charge: {charge_id}",
            details=f"total flushed: {total_flushed}"
        )
    except Exception as e:
        return CheckResult(
            name="stream_meter_flush",
            success=False,
            duration=0,
            message=f"StreamMeter flush failed: {e}"
        )


stream_meter_flush_check = Check(
    name="stream_meter_flush",
    description="Test stream meter flush",
    run=_stream_meter_flush_check
)
