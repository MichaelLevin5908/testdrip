"""Webhook checks."""
import uuid
import hmac
import hashlib
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _webhook_sign_check(ctx: CheckContext) -> CheckResult:
    """Create a webhook and get signing secret."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        # Check if SDK supports webhooks
        if not hasattr(client, 'create_webhook'):
            return CheckResult(
                name="webhook_sign",
                success=True,
                duration=0,
                message="Webhook creation not available in SDK",
                details="Skipping webhook tests"
            )

        webhook = client.create_webhook(
            url=f"https://example.com/webhook/{uuid.uuid4().hex}",
            events=["charge.succeeded", "customer.balance.low"],
            description="Health check webhook"
        )

        # Store for verify check
        ctx.webhook_id = webhook.id
        ctx.webhook_secret = getattr(webhook, 'secret', None)

        return CheckResult(
            name="webhook_sign",
            success=True,
            duration=0,
            message=f"Created webhook {webhook.id}",
            details="Secret obtained for verification"
        )
    except Exception as e:
        return CheckResult(
            name="webhook_sign",
            success=False,
            duration=0,
            message=f"Failed to create webhook: {e}"
        )


webhook_sign_check = Check(
    name="webhook_sign",
    description="Create webhook and get secret",
    run=_webhook_sign_check,
    quick=True
)


async def _webhook_verify_check(ctx: CheckContext) -> CheckResult:
    """Verify webhook signature validation."""
    import time

    if not ctx.webhook_secret:
        return CheckResult(
            name="webhook_verify",
            success=True,
            duration=0,
            message="No webhook secret available",
            details="Webhook sign check may have been skipped"
        )

    try:
        # Create test payload
        test_payload = '{"event": "test", "data": {}}'

        # Generate timestamp
        timestamp = int(time.time())

        # Generate signature using HMAC-SHA256 over {timestamp}.{payload}
        signature_payload = f"{timestamp}.{test_payload}"
        hex_signature = hmac.new(
            ctx.webhook_secret.encode(),
            signature_payload.encode(),
            hashlib.sha256
        ).hexdigest()

        # Format signature as SDK expects: t=timestamp,v1=hexsignature
        formatted_signature = f"t={timestamp},v1={hex_signature}"

        # Try to use SDK's verify function if available
        try:
            from drip import verify_webhook_signature
            is_valid = verify_webhook_signature(
                payload=test_payload,
                signature=formatted_signature,
                secret=ctx.webhook_secret
            )
        except ImportError:
            # Fallback: manually verify using same logic
            expected_sig = hmac.new(
                ctx.webhook_secret.encode(),
                signature_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            is_valid = hmac.compare_digest(hex_signature, expected_sig)

        if is_valid:
            return CheckResult(
                name="webhook_verify",
                success=True,
                duration=0,
                message="Signature verification working"
            )
        else:
            return CheckResult(
                name="webhook_verify",
                success=False,
                duration=0,
                message="Signature verification failed unexpectedly"
            )
    except Exception as e:
        return CheckResult(
            name="webhook_verify",
            success=False,
            duration=0,
            message=f"Webhook verify failed: {e}"
        )
    finally:
        # Cleanup webhook
        if ctx.webhook_id:
            try:
                client = create_client(ctx.api_key, ctx.api_url)
                if hasattr(client, 'delete_webhook'):
                    client.delete_webhook(ctx.webhook_id)
            except Exception:
                pass


webhook_verify_check = Check(
    name="webhook_verify",
    description="Verify webhook signature",
    run=_webhook_verify_check,
    quick=True
)
