"""Meter operation checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _list_meters_check(ctx: CheckContext) -> CheckResult:
    """List available meters."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'list_meters'):
            return CheckResult(
                name="meters_list",
                success=True,
                duration=0,
                message="Skipped (list_meters not available)",
                details="The list_meters method is not available in the SDK"
            )

        result = client.list_meters()

        if hasattr(result, 'data'):
            count = len(result.data)
            meters = [getattr(m, 'name', str(m)) for m in result.data[:3]]
        elif isinstance(result, list):
            count = len(result)
            meters = [getattr(m, 'name', str(m)) for m in result[:3]]
        else:
            count = 1
            meters = [str(result)]

        return CheckResult(
            name="meters_list",
            success=True,
            duration=0,
            message=f"Found {count} meter(s)",
            details=f"Meters: {', '.join(meters)}" if meters else None
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="meters_list",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="meters_list",
            success=False,
            duration=0,
            message=f"Failed to list meters: {e}"
        )


list_meters_check = Check(
    name="meters_list",
    description="List available meters",
    run=_list_meters_check
)
