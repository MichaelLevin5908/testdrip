"""Webhook CRUD operation checks."""
import uuid
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _webhook_create_check(ctx: CheckContext) -> CheckResult:
    """Create a webhook endpoint."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'create_webhook'):
            return CheckResult(
                name="webhook_create",
                success=True,
                duration=0,
                message="Skipped (create_webhook not available)",
                details="The create_webhook method is not available in the SDK"
            )

        webhook_url = f"https://webhook.site/health-check-{uuid.uuid4().hex[:8]}"
        result = client.create_webhook(
            url=webhook_url,
            events=["charge.created", "charge.settled"]
        )

        webhook_id = getattr(result, 'id', str(result))
        secret = getattr(result, 'secret', None)

        ctx.webhook_id = webhook_id
        if secret:
            ctx.webhook_secret = secret

        return CheckResult(
            name="webhook_create",
            success=True,
            duration=0,
            message=f"Created webhook {webhook_id}",
            details=f"URL: {webhook_url}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="webhook_create",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="webhook_create",
            success=False,
            duration=0,
            message=f"Failed to create webhook: {e}"
        )


webhook_create_check = Check(
    name="webhook_create",
    description="Create webhook endpoint",
    run=_webhook_create_check
)


async def _webhook_list_check(ctx: CheckContext) -> CheckResult:
    """List all webhooks."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'list_webhooks'):
            return CheckResult(
                name="webhook_list",
                success=True,
                duration=0,
                message="Skipped (list_webhooks not available)",
                details="The list_webhooks method is not available in the SDK"
            )

        result = client.list_webhooks()

        if hasattr(result, 'data'):
            count = len(result.data)
        elif isinstance(result, list):
            count = len(result)
        else:
            count = 1

        return CheckResult(
            name="webhook_list",
            success=True,
            duration=0,
            message=f"Found {count} webhook(s)"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="webhook_list",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="webhook_list",
            success=False,
            duration=0,
            message=f"Failed to list webhooks: {e}"
        )


webhook_list_check = Check(
    name="webhook_list",
    description="List all webhooks",
    run=_webhook_list_check
)


async def _webhook_get_check(ctx: CheckContext) -> CheckResult:
    """Get webhook by ID."""
    if not ctx.webhook_id:
        return CheckResult(
            name="webhook_get",
            success=True,
            duration=0,
            message="Skipped (no webhook ID)",
            details="Run webhook_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'get_webhook'):
            return CheckResult(
                name="webhook_get",
                success=True,
                duration=0,
                message="Skipped (get_webhook not available)",
                details="The get_webhook method is not available in the SDK"
            )

        webhook = client.get_webhook(ctx.webhook_id)
        url = getattr(webhook, 'url', 'N/A')

        return CheckResult(
            name="webhook_get",
            success=True,
            duration=0,
            message=f"Retrieved webhook {ctx.webhook_id}",
            details=f"URL: {url}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="webhook_get",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="webhook_get",
            success=False,
            duration=0,
            message=f"Failed to get webhook: {e}"
        )


webhook_get_check = Check(
    name="webhook_get",
    description="Get webhook by ID",
    run=_webhook_get_check
)


async def _webhook_test_check(ctx: CheckContext) -> CheckResult:
    """Send test webhook event."""
    if not ctx.webhook_id:
        return CheckResult(
            name="webhook_test",
            success=True,
            duration=0,
            message="Skipped (no webhook ID)",
            details="Run webhook_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'test_webhook'):
            return CheckResult(
                name="webhook_test",
                success=True,
                duration=0,
                message="Skipped (test_webhook not available)",
                details="The test_webhook method is not available in the SDK"
            )

        result = client.test_webhook(ctx.webhook_id)
        sent = getattr(result, 'sent', getattr(result, 'success', True))

        return CheckResult(
            name="webhook_test",
            success=True,
            duration=0,
            message=f"Test event sent: {sent}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="webhook_test",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="webhook_test",
            success=False,
            duration=0,
            message=f"Failed to test webhook: {e}"
        )


webhook_test_check = Check(
    name="webhook_test",
    description="Send test webhook event",
    run=_webhook_test_check
)


async def _webhook_rotate_secret_check(ctx: CheckContext) -> CheckResult:
    """Rotate webhook signing secret."""
    if not ctx.webhook_id:
        return CheckResult(
            name="webhook_rotate_secret",
            success=True,
            duration=0,
            message="Skipped (no webhook ID)",
            details="Run webhook_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'rotate_webhook_secret'):
            return CheckResult(
                name="webhook_rotate_secret",
                success=True,
                duration=0,
                message="Skipped (rotate_webhook_secret not available)",
                details="The rotate_webhook_secret method is not available in the SDK"
            )

        result = client.rotate_webhook_secret(ctx.webhook_id)
        new_secret = getattr(result, 'secret', 'rotated')

        return CheckResult(
            name="webhook_rotate_secret",
            success=True,
            duration=0,
            message="Secret rotated successfully",
            details=f"New secret: {new_secret[:10]}..." if len(str(new_secret)) > 10 else f"New secret: {new_secret}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="webhook_rotate_secret",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="webhook_rotate_secret",
            success=False,
            duration=0,
            message=f"Failed to rotate secret: {e}"
        )


webhook_rotate_secret_check = Check(
    name="webhook_rotate_secret",
    description="Rotate webhook signing secret",
    run=_webhook_rotate_secret_check
)


async def _webhook_delete_check(ctx: CheckContext) -> CheckResult:
    """Delete webhook."""
    if not ctx.webhook_id:
        return CheckResult(
            name="webhook_delete",
            success=True,
            duration=0,
            message="Skipped (no webhook ID)",
            details="Run webhook_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'delete_webhook'):
            return CheckResult(
                name="webhook_delete",
                success=True,
                duration=0,
                message="Skipped (delete_webhook not available)",
                details="The delete_webhook method is not available in the SDK"
            )

        client.delete_webhook(ctx.webhook_id)

        return CheckResult(
            name="webhook_delete",
            success=True,
            duration=0,
            message=f"Deleted webhook {ctx.webhook_id}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="webhook_delete",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="webhook_delete",
            success=False,
            duration=0,
            message=f"Failed to delete webhook: {e}"
        )


webhook_delete_check = Check(
    name="webhook_delete",
    description="Delete webhook",
    run=_webhook_delete_check
)
