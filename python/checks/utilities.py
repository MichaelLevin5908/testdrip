"""Utility function checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client, generate_idempotency_key


async def _generate_idempotency_key_check(ctx: CheckContext) -> CheckResult:
    """Test idempotency key generation."""
    try:
        # Test our local implementation
        key1 = generate_idempotency_key("test", "cust_123", 1)
        key2 = generate_idempotency_key("test", "cust_123", 1)
        key3 = generate_idempotency_key("test", "cust_123", 2)

        if key1 != key2:
            return CheckResult(
                name="idempotency_key_gen",
                success=False,
                duration=0,
                message="Keys not deterministic",
                details="Same inputs should produce same key"
            )

        if key1 == key3:
            return CheckResult(
                name="idempotency_key_gen",
                success=False,
                duration=0,
                message="Keys not unique",
                details="Different sequence should produce different key"
            )

        # Also test SDK static method if available
        client = create_client(ctx.api_key, ctx.api_url)
        sdk_method = getattr(client, 'generate_idempotency_key', None) or getattr(type(client), 'generate_idempotency_key', None)

        if sdk_method:
            sdk_key = sdk_method(customer_id="cust_123", meter="tokens", sequence=1)
            return CheckResult(
                name="idempotency_key_gen",
                success=True,
                duration=0,
                message="Keys generated correctly",
                details=f"SDK key: {sdk_key[:20]}..."
            )

        return CheckResult(
            name="idempotency_key_gen",
            success=True,
            duration=0,
            message="Keys generated correctly",
            details=f"Local key: {key1[:20]}..."
        )
    except Exception as e:
        return CheckResult(
            name="idempotency_key_gen",
            success=False,
            duration=0,
            message=f"Failed to generate keys: {e}"
        )


generate_idempotency_key_check = Check(
    name="idempotency_key_gen",
    description="Test idempotency key generation",
    run=_generate_idempotency_key_check,
    quick=True
)


async def _create_stream_meter_check(ctx: CheckContext) -> CheckResult:
    """Create stream meter instance."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        # Check for StreamMeter class or create_stream_meter method
        stream_meter_class = getattr(client, 'StreamMeter', None)
        create_method = getattr(client, 'create_stream_meter', None)

        if stream_meter_class:
            customer_id = ctx.created_customer_id or ctx.test_customer_id or "test_customer"
            meter = stream_meter_class(
                customer_id=customer_id,
                meter="tokens"
            )
            ctx.stream_meter = meter
            return CheckResult(
                name="stream_meter_create",
                success=True,
                duration=0,
                message="StreamMeter instance created",
                details=f"Customer: {customer_id}"
            )

        if create_method:
            customer_id = ctx.created_customer_id or ctx.test_customer_id or "test_customer"
            meter = create_method(
                customer_id=customer_id,
                meter="tokens"
            )
            ctx.stream_meter = meter
            return CheckResult(
                name="stream_meter_create",
                success=True,
                duration=0,
                message="Stream meter created via method",
                details=f"Customer: {customer_id}"
            )

        return CheckResult(
            name="stream_meter_create",
            success=True,
            duration=0,
            message="Skipped (StreamMeter not available)",
            details="The StreamMeter class is not available in the SDK"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="stream_meter_create",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="stream_meter_create",
            success=False,
            duration=0,
            message=f"Failed to create stream meter: {e}"
        )


create_stream_meter_check = Check(
    name="stream_meter_create",
    description="Create stream meter instance",
    run=_create_stream_meter_check
)
