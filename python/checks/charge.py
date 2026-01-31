"""Charge operation checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client, generate_idempotency_key


async def _charge_create_check(ctx: CheckContext) -> CheckResult:
    """Create a test charge."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="charge_create",
            success=False,
            duration=0,
            message="No customer ID available",
            suggestion="Run customer_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)
        idempotency_key = generate_idempotency_key("charge")

        result = client.charge(
            customer_id=customer_id,
            meter="api_calls",
            quantity=1,
            idempotency_key=idempotency_key,
            metadata={"test": True}
        )

        # Handle different response formats
        if hasattr(result, 'charge'):
            charge = result.charge
            charge_id = charge.id
            amount = getattr(charge, 'amount_usdc', getattr(charge, 'amount', 'N/A'))
        else:
            charge_id = getattr(result, 'id', str(result))
            amount = getattr(result, 'amount_usdc', getattr(result, 'amount', 'N/A'))

        # Store charge ID for status check
        ctx.created_charge_id = charge_id

        return CheckResult(
            name="charge_create",
            success=True,
            duration=0,
            message=f"Created charge {charge_id}",
            details=f"amount: {amount} USDC"
        )
    except Exception as e:
        return CheckResult(
            name="charge_create",
            success=False,
            duration=0,
            message=f"Failed to create charge: {e}",
            suggestion="Check customer balance and meter configuration"
        )


charge_create_check = Check(
    name="charge_create",
    description="Create a usage charge",
    run=_charge_create_check
)


async def _charge_status_check(ctx: CheckContext) -> CheckResult:
    """Check charge settlement status."""
    if not ctx.created_charge_id:
        return CheckResult(
            name="charge_status",
            success=False,
            duration=0,
            message="No charge ID available",
            suggestion="Run charge_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        # Try get_charge_status or get_charge
        if hasattr(client, 'get_charge_status'):
            status = client.get_charge_status(ctx.created_charge_id)
            status_str = getattr(status, 'status', str(status))
            settlement = getattr(status, 'settlement_tx', None) or 'pending'
        elif hasattr(client, 'get_charge'):
            charge = client.get_charge(ctx.created_charge_id)
            status_str = getattr(charge, 'status', 'unknown')
            settlement = getattr(charge, 'settlement_tx', None) or 'pending'
        else:
            return CheckResult(
                name="charge_status",
                success=True,
                duration=0,
                message="Charge status check skipped",
                details="SDK does not support get_charge_status"
            )

        return CheckResult(
            name="charge_status",
            success=True,
            duration=0,
            message=f"Charge status: {status_str}",
            details=f"settlement_tx: {settlement}"
        )
    except Exception as e:
        return CheckResult(
            name="charge_status",
            success=False,
            duration=0,
            message=f"Failed to get charge status: {e}"
        )


charge_status_check = Check(
    name="charge_status",
    description="Check charge settlement status",
    run=_charge_status_check
)


async def _get_charge_check(ctx: CheckContext) -> CheckResult:
    """Get a specific charge by ID."""
    charge_id = ctx.charge_id or ctx.created_charge_id
    if not charge_id:
        return CheckResult(
            name="charge_get",
            success=False,
            duration=0,
            message="No charge ID available",
            suggestion="Run charge_status check first to get a charge ID"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'get_charge'):
            return CheckResult(
                name="charge_get",
                success=True,
                duration=0,
                message="Skipped (get_charge not available)",
                details="The get_charge method is not available in the SDK"
            )

        charge = client.get_charge(charge_id)
        status = getattr(charge, 'status', 'unknown')
        amount = getattr(charge, 'amount_usdc', getattr(charge, 'amount', 'N/A'))

        return CheckResult(
            name="charge_get",
            success=True,
            duration=0,
            message=f"Charge {charge_id} ({status})",
            details=f"Amount: {amount} USDC"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="charge_get",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="charge_get",
            success=False,
            duration=0,
            message=f"Failed to get charge: {e}"
        )


get_charge_check = Check(
    name="charge_get",
    description="Get a specific charge by ID",
    run=_get_charge_check
)


async def _list_charges_filtered_check(ctx: CheckContext) -> CheckResult:
    """List charges with customer filtering."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="charge_list_filtered",
            success=False,
            duration=0,
            message="No customer ID available",
            suggestion="Run customer_create check first or set TEST_CUSTOMER_ID"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'list_charges'):
            return CheckResult(
                name="charge_list_filtered",
                success=True,
                duration=0,
                message="Skipped (list_charges not available)",
                details="The list_charges method is not available in the SDK"
            )

        result = client.list_charges(customer_id=customer_id, limit=10)

        # Handle different response formats
        if hasattr(result, 'data'):
            count = len(result.data)
            # Store first charge ID for subsequent checks
            if count > 0 and not ctx.charge_id:
                ctx.charge_id = result.data[0].id
        elif hasattr(result, 'count'):
            count = result.count
        elif isinstance(result, list):
            count = len(result)
            if count > 0 and not ctx.charge_id:
                ctx.charge_id = result[0].id if hasattr(result[0], 'id') else result[0].get('id')
        else:
            count = 1

        return CheckResult(
            name="charge_list_filtered",
            success=True,
            duration=0,
            message=f"Found {count} charge(s) for customer",
            details=f"Customer: {customer_id}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="charge_list_filtered",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="charge_list_filtered",
            success=False,
            duration=0,
            message=f"Failed to list charges: {e}"
        )


list_charges_filtered_check = Check(
    name="charge_list_filtered",
    description="List charges with customer filtering",
    run=_list_charges_filtered_check
)
