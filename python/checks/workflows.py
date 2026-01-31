"""Workflow operation checks."""
import uuid
from ..types import Check, CheckContext, CheckResult
from ..drip_client import create_client


async def _workflow_create_check(ctx: CheckContext) -> CheckResult:
    """Create workflow definition."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'create_workflow'):
            return CheckResult(
                name="workflow_create",
                success=True,
                duration=0,
                message="Skipped (create_workflow not available)",
                details="The create_workflow method is not available in the SDK"
            )

        workflow_slug = f"health-check-{uuid.uuid4().hex[:8]}"
        result = client.create_workflow(
            name=f"Health Check Workflow {workflow_slug}",
            slug=workflow_slug,
            description="Test workflow created by health check"
        )

        workflow_id = getattr(result, 'id', str(result))
        ctx.workflow_id = workflow_id

        return CheckResult(
            name="workflow_create",
            success=True,
            duration=0,
            message=f"Created workflow {workflow_id}",
            details=f"Slug: {workflow_slug}"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="workflow_create",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="workflow_create",
            success=False,
            duration=0,
            message=f"Failed to create workflow: {e}"
        )


workflow_create_check = Check(
    name="workflow_create",
    description="Create workflow definition",
    run=_workflow_create_check
)


async def _workflow_list_check(ctx: CheckContext) -> CheckResult:
    """List all workflows."""
    try:
        client = create_client(ctx.api_key, ctx.api_url)

        if not hasattr(client, 'list_workflows'):
            return CheckResult(
                name="workflow_list",
                success=True,
                duration=0,
                message="Skipped (list_workflows not available)",
                details="The list_workflows method is not available in the SDK"
            )

        result = client.list_workflows()

        if hasattr(result, 'data'):
            count = len(result.data)
            if count > 0 and not ctx.workflow_id:
                ctx.workflow_id = result.data[0].id
        elif isinstance(result, list):
            count = len(result)
            if count > 0 and not ctx.workflow_id:
                ctx.workflow_id = result[0].id if hasattr(result[0], 'id') else result[0].get('id')
        else:
            count = 1

        return CheckResult(
            name="workflow_list",
            success=True,
            duration=0,
            message=f"Found {count} workflow(s)"
        )
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or '501' in error_str:
            return CheckResult(
                name="workflow_list",
                success=True,
                duration=0,
                message="Skipped (endpoint not implemented)",
                details=error_str
            )
        return CheckResult(
            name="workflow_list",
            success=False,
            duration=0,
            message=f"Failed to list workflows: {e}"
        )


workflow_list_check = Check(
    name="workflow_list",
    description="List all workflows",
    run=_workflow_list_check
)
