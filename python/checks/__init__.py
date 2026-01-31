"""Export all checks matching TypeScript version (42 checks)."""
from .connectivity import connectivity_check, authentication_check
from .customer import (
    customer_create_check,
    customer_get_check,
    customer_list_check,
    customer_cleanup_check
)
from .charge import (
    charge_create_check,
    charge_status_check,
    get_charge_check,
    list_charges_filtered_check
)
from .balance import balance_get_check
from .streaming import stream_meter_add_check, stream_meter_flush_check
from .idempotency import idempotency_check
from .webhooks import webhook_sign_check, webhook_verify_check
from .webhooks_crud import (
    webhook_create_check,
    webhook_list_check,
    webhook_get_check,
    webhook_test_check,
    webhook_rotate_secret_check,
    webhook_delete_check
)
from .runs import (
    run_create_check,
    run_timeline_check,
    run_end_check,
    emit_event_check,
    emit_events_batch_check,
    record_run_check
)
from .workflows import workflow_create_check, workflow_list_check
from .usage import track_usage_check
from .wrap_api_call import (
    wrap_api_call_basic_check,
    wrap_api_call_idempotency_check,
    wrap_api_call_error_handling_check
)
from .checkout import checkout_create_check
from .meters import list_meters_check
from .estimates import estimate_from_usage_check, estimate_from_hypothetical_check
from .resilience import get_metrics_check, get_health_check
from .utilities import generate_idempotency_key_check, create_stream_meter_check

# All 42 checks in order (matching TypeScript version, cleanup last)
all_checks = [
    # Connectivity & auth (2)
    connectivity_check,
    authentication_check,

    # Customer operations (3)
    customer_create_check,
    customer_get_check,
    customer_list_check,

    # Charge operations (4)
    charge_create_check,
    charge_status_check,
    get_charge_check,
    list_charges_filtered_check,

    # Usage tracking (2)
    track_usage_check,
    balance_get_check,

    # Streaming (2)
    stream_meter_add_check,
    stream_meter_flush_check,

    # Idempotency (1)
    idempotency_check,

    # API wrapping (3)
    wrap_api_call_basic_check,
    wrap_api_call_idempotency_check,
    wrap_api_call_error_handling_check,

    # Checkout (1)
    checkout_create_check,

    # Webhook signature (quick checks) (2)
    webhook_sign_check,
    webhook_verify_check,

    # Webhooks CRUD (6)
    webhook_create_check,
    webhook_list_check,
    webhook_get_check,
    webhook_test_check,
    webhook_rotate_secret_check,
    webhook_delete_check,

    # Workflows (2)
    workflow_create_check,
    workflow_list_check,

    # Runs (6)
    run_create_check,
    run_timeline_check,
    run_end_check,
    emit_event_check,
    emit_events_batch_check,
    record_run_check,

    # Meters (1)
    list_meters_check,

    # Estimates (2)
    estimate_from_usage_check,
    estimate_from_hypothetical_check,

    # Resilience (2)
    get_metrics_check,
    get_health_check,

    # Utilities (2)
    generate_idempotency_key_check,
    create_stream_meter_check,

    # Cleanup (always last) (1)
    customer_cleanup_check,
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
