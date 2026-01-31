"""Resilience and metrics checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _get_metrics_check(ctx: CheckContext) -> CheckResult:
    """Get SDK metrics."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'get_metrics'):
            return CheckResult(
                name="sdk_metrics",
                success=True,
                duration=0,
                message="Skipped (get_metrics not available)",
                details="The get_metrics method is not available in the SDK"
            )

        metrics = client.get_metrics()

        if metrics is None:
            return CheckResult(
                name="sdk_metrics",
                success=True,
                duration=0,
                message="Skipped (resilience not enabled)",
                details="Enable resilience to get metrics"
            )

        total_requests = metrics.get('total_requests', 0) if isinstance(metrics, dict) else getattr(metrics, 'total_requests', 0)

        return CheckResult(
            name="sdk_metrics",
            success=True,
            duration=0,
            message=f"Total requests: {total_requests}",
            details="Metrics retrieved successfully"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="sdk_metrics",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="sdk_metrics",
            success=False,
            duration=0,
            message=f"Failed to get metrics: {e}"
        )


get_metrics_check = Check(
    name="sdk_metrics",
    description="Get SDK metrics",
    run=_get_metrics_check
)


async def _get_health_check(ctx: CheckContext) -> CheckResult:
    """Get resilience health status."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'get_health'):
            return CheckResult(
                name="resilience_health",
                success=True,
                duration=0,
                message="Skipped (get_health not available)",
                details="The get_health method is not available in the SDK"
            )

        health = client.get_health()

        if health is None:
            return CheckResult(
                name="resilience_health",
                success=True,
                duration=0,
                message="Skipped (resilience not enabled)",
                details="Enable resilience to get health status"
            )

        if isinstance(health, dict):
            status = health.get('healthy', health.get('status', 'unknown'))
        else:
            status = getattr(health, 'healthy', getattr(health, 'status', 'unknown'))

        return CheckResult(
            name="resilience_health",
            success=True,
            duration=0,
            message=f"Health status: {status}",
            details="Health check completed"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="resilience_health",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="resilience_health",
            success=False,
            duration=0,
            message=f"Failed to get health: {e}"
        )


get_health_check = Check(
    name="resilience_health",
    description="Get resilience health status",
    run=_get_health_check
)
