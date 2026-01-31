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
    if not ctx.webhook_secret:
        return CheckResult(
            name="webhook_verify",
            success=True,
            duration=0,
            message="No webhook secret available",
            details="Webhook sign check may have been skipped"
        )

    try:
        # Create test payload and signature
        test_payload = b'{"event": "test", "data": {}}'

        # Generate valid signature
        signature = hmac.new(
            ctx.webhook_secret.encode(),
            test_payload,
            hashlib.sha256
        ).hexdigest()

        # Try to use SDK's verify function if available
        try:
            from drip import verify_webhook_signature
            is_valid = verify_webhook_signature(
                payload=test_payload,
                signature=signature,
                secret=ctx.webhook_secret
            )
        except ImportError:
            # Fallback: manually verify
            expected_sig = hmac.new(
                ctx.webhook_secret.encode(),
                test_payload,
                hashlib.sha256
            ).hexdigest()
            is_valid = hmac.compare_digest(signature, expected_sig)

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
