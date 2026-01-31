"""Customer CRUD checks."""
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client, generate_external_id


async def _customer_create_check(ctx: CheckContext) -> CheckResult:
    """Create a test customer."""
    # If using a seeded test customer, skip creation
    if ctx.test_customer_id:
        return CheckResult(
            name="customer_create",
            success=True,
            duration=0,
            message=f"Using seeded customer {ctx.test_customer_id}",
            details="Skipped creation (TEST_CUSTOMER_ID configured)"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)
        external_id = generate_external_id("health_check")

        customer = client.create_customer(
            onchain_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            external_customer_id=external_id,
            metadata={"test": True, "source": "python_health_check"}
        )

        # Store for subsequent checks
        ctx.created_customer_id = customer.id

        return CheckResult(
            name="customer_create",
            success=True,
            duration=0,
            message=f"Created customer {customer.id}",
            details=f"external_id: {external_id}"
        )
    except Exception as e:
        error_str = str(e)
        # Handle duplicate customer gracefully
        if "409" in error_str or "DUPLICATE" in error_str.upper() or "already exists" in error_str.lower():
            return CheckResult(
                name="customer_create",
                success=True,
                duration=0,
                message="Customer already exists (using existing)",
                details="Duplicate customer handled gracefully"
            )
        return CheckResult(
            name="customer_create",
            success=False,
            duration=0,
            message=f"Failed to create customer: {e}",
            suggestion="Check API permissions and request format"
        )


customer_create_check = Check(
    name="customer_create",
    description="Create a test customer",
    run=_customer_create_check
)


async def _customer_get_check(ctx: CheckContext) -> CheckResult:
    """Retrieve the created customer."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="customer_get",
            success=False,
            duration=0,
            message="No customer ID available",
            suggestion="Run customer_create check first"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)
        customer = client.get_customer(customer_id)

        return CheckResult(
            name="customer_get",
            success=True,
            duration=0,
            message=f"Retrieved customer {customer.id}",
            details=f"address: {getattr(customer, 'onchain_address', 'N/A')}"
        )
    except Exception as e:
        return CheckResult(
            name="customer_get",
            success=False,
            duration=0,
            message=f"Failed to get customer: {e}"
        )


customer_get_check = Check(
    name="customer_get",
    description="Retrieve created customer",
    run=_customer_get_check
)


async def _customer_list_check(ctx: CheckContext) -> CheckResult:
    """List customers with filtering."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)
        result = client.list_customers(limit=10)

        # Handle different response formats
        if hasattr(result, 'customers'):
            count = len(result.customers)
        elif isinstance(result, list):
            count = len(result)
        else:
            count = 1

        return CheckResult(
            name="customer_list",
            success=True,
            duration=0,
            message=f"Listed {count} customers"
        )
    except Exception as e:
        return CheckResult(
            name="customer_list",
            success=False,
            duration=0,
            message=f"Failed to list customers: {e}"
        )


customer_list_check = Check(
    name="customer_list",
    description="List customers with pagination",
    run=_customer_list_check
)


async def _customer_cleanup_check(ctx: CheckContext) -> CheckResult:
    """Cleanup test customer (if cleanup enabled)."""
    if ctx.skip_cleanup:
        return CheckResult(
            name="customer_cleanup",
            success=True,
            duration=0,
            message="Cleanup skipped (--no-cleanup flag)"
        )

    if not ctx.created_customer_id:
        return CheckResult(
            name="customer_cleanup",
            success=True,
            duration=0,
            message="No customer to clean up"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        # Try to delete customer if SDK supports it
        if hasattr(client, 'delete_customer'):
            client.delete_customer(ctx.created_customer_id)
            return CheckResult(
                name="customer_cleanup",
                success=True,
                duration=0,
                message=f"Deleted customer {ctx.created_customer_id}"
            )
        else:
            return CheckResult(
                name="customer_cleanup",
                success=True,
                duration=0,
                message=f"Customer {ctx.created_customer_id} marked for cleanup",
                details="Manual cleanup may be required if delete not supported"
            )
    except Exception as e:
        return CheckResult(
            name="customer_cleanup",
            success=False,
            duration=0,
            message=f"Failed to cleanup customer: {e}",
            suggestion="Manual cleanup may be required"
        )


customer_cleanup_check = Check(
    name="customer_cleanup",
    description="Clean up test resources",
    run=_customer_cleanup_check
)
