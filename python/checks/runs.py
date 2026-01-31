"""Execution run checks."""
import uuid
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _run_create_check(ctx: CheckContext) -> CheckResult:
    """Create a workflow run."""
    customer_id = ctx.created_customer_id or ctx.test_customer_id
    if not customer_id:
        return CheckResult(
            name="run_create",
            success=False,
            duration=0,
            message="No customer ID available"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        # Check if SDK supports runs
        if not hasattr(client, 'start_run') and not hasattr(client, 'record_run'):
            return CheckResult(
                name="run_create",
                success=True,
                duration=0,
                message="Run tracking not available in SDK",
                details="Skipping run tests"
            )

        workflow_slug = f"health-check-{uuid.uuid4().hex[:8]}"
        correlation_id = f"health_{uuid.uuid4().hex[:8]}"

        # Prefer record_run as it's simpler and handles workflow creation automatically
        if hasattr(client, 'record_run'):
            result = client.record_run(
                customer_id=customer_id,
                workflow=workflow_slug,  # SDK auto-creates workflow from slug
                status="COMPLETED",
                events=[
                    {
                        "eventType": "test.event",
                        "quantity": 100,
                        "units": "tokens",
                        "description": "Health check test event"
                    }
                ]
            )
            run_info = getattr(result, 'run', result)
            run_id = getattr(run_info, 'id', str(result))
            ctx.run_id = run_id

            return CheckResult(
                name="run_create",
                success=True,
                duration=0,
                message=f"Created and completed run {run_id}",
                details=f"workflow: {workflow_slug}"
            )

        # Fallback to start_run if record_run not available
        if hasattr(client, 'start_run'):
            # Must create workflow first for start_run
            if hasattr(client, 'create_workflow'):
                try:
                    workflow = client.create_workflow(
                        name="Health Check Workflow",
                        slug=workflow_slug,
                        product_surface="AGENT"
                    )
                    workflow_id = workflow.id
                except Exception:
                    # Workflow might already exist
                    workflow_id = workflow_slug
            else:
                return CheckResult(
                    name="run_create",
                    success=True,
                    duration=0,
                    message="Run tracking requires workflow creation",
                    details="create_workflow not available in SDK"
                )

            run = client.start_run(
                customer_id=customer_id,
                workflow_id=workflow_id,
                correlation_id=correlation_id
            )
            run_id = run.id

            # Emit an event if supported
            if hasattr(client, 'emit_event'):
                client.emit_event(
                    run_id=run_id,
                    event_type="test.event",
                    quantity=100,
                    units="tokens"
                )

            # End run
            if hasattr(client, 'end_run'):
                client.end_run(run_id, status="COMPLETED")

            ctx.run_id = run_id

            return CheckResult(
                name="run_create",
                success=True,
                duration=0,
                message=f"Created and completed run {run_id}",
                details=f"workflow: {workflow_slug}"
            )

        return CheckResult(
            name="run_create",
            success=True,
            duration=0,
            message="Run methods available but could not execute",
            details="Skipping run tests"
        )
    except Exception as e:
        return CheckResult(
            name="run_create",
            success=False,
            duration=0,
            message=f"Run creation failed: {e}"
        )


run_create_check = Check(
    name="run_create",
    description="Create and complete a workflow run",
    run=_run_create_check
)


async def _run_timeline_check(ctx: CheckContext) -> CheckResult:
    """Get run timeline."""
    if not ctx.run_id:
        return CheckResult(
            name="run_timeline",
            success=True,
            duration=0,
            message="No run ID available",
            details="Run create check may have been skipped"
        )

    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'get_run_timeline'):
            return CheckResult(
                name="run_timeline",
                success=True,
                duration=0,
                message="Run timeline not available in SDK",
                details="Skipping timeline check"
            )

        timeline = client.get_run_timeline(ctx.run_id)

        # Handle different response formats
        if hasattr(timeline, 'events'):
            event_count = len(timeline.events)
        elif isinstance(timeline, list):
            event_count = len(timeline)
        else:
            event_count = 1

        return CheckResult(
            name="run_timeline",
            success=True,
            duration=0,
            message=f"Retrieved timeline with {event_count} events"
        )
    except Exception as e:
        return CheckResult(
            name="run_timeline",
            success=False,
            duration=0,
            message=f"Failed to get timeline: {e}"
        )


run_timeline_check = Check(
    name="run_timeline",
    description="Get run timeline",
    run=_run_timeline_check
)
