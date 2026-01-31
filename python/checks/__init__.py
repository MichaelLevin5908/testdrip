"""Export all checks matching TypeScript version."""
from .connectivity import connectivity_check, authentication_check
from .customer import (
    customer_create_check,
    customer_get_check,
    customer_list_check,
    customer_cleanup_check
)
from .charge import charge_create_check, charge_status_check
from .balance import balance_get_check
from .streaming import stream_meter_add_check, stream_meter_flush_check
from .idempotency import idempotency_check
from .webhooks import webhook_sign_check, webhook_verify_check
from .runs import run_create_check, run_timeline_check
from .usage import track_usage_check
from .wrap_api_call import (
    wrap_api_call_basic_check,
    wrap_api_call_idempotency_check,
    wrap_api_call_error_handling_check
)

# All checks in order (cleanup last)
all_checks = [
    connectivity_check,
    authentication_check,
    customer_create_check,
    customer_get_check,
    customer_list_check,
    charge_create_check,
    charge_status_check,
    balance_get_check,
    stream_meter_add_check,
    stream_meter_flush_check,
    idempotency_check,
    webhook_sign_check,
    webhook_verify_check,
    run_create_check,
    run_timeline_check,
    track_usage_check,
    wrap_api_call_basic_check,
    wrap_api_call_idempotency_check,
    wrap_api_call_error_handling_check,
    customer_cleanup_check,  # Always last
]

# Quick checks for smoke testing
quick_checks = [c for c in all_checks if c.quick]


def get_checks_by_name(names: list) -> list:
    """Get checks by name (case-insensitive, partial match)."""
    result = []
    for name in names:
        name_lower = name.lower().strip()
        for check in all_checks:
            if name_lower in check.name.lower():
                if check not in result:
                    result.append(check)
    return result
