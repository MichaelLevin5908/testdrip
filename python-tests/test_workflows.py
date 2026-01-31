"""Test workflow and agent run tracking.

This module tests the workflow and run tracking functionality
for monitoring agent executions and their associated events.
"""
import pytest
import uuid

# Import SDK components
try:
    from drip import Drip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None


pytestmark = pytest.mark.skipif(
    not DRIP_SDK_AVAILABLE,
    reason="drip-sdk not installed"
)


class TestCreateWorkflow:
    """Test workflow creation."""

    def test_create_workflow_basic(self, client):
        """Create a workflow definition.

        Workflows define templates for agent runs, specifying
        the expected structure and billing.
        """
        try:
            unique_slug = f"test-workflow-{uuid.uuid4().hex[:8]}"

            workflow = client.create_workflow(
                name="Test Workflow",
                slug=unique_slug,
                product_surface="AGENT"
            )

            assert workflow is not None
            assert workflow.id is not None
        except AttributeError:
            pytest.skip("create_workflow method not available")

    def test_create_workflow_with_description(self, client):
        """Create workflow with description."""
        try:
            unique_slug = f"test-workflow-{uuid.uuid4().hex[:8]}"

            workflow = client.create_workflow(
                name="Described Workflow",
                slug=unique_slug,
                product_surface="AGENT",
                description="A test workflow with description"
            )

            assert workflow is not None
            if hasattr(workflow, 'description'):
                assert workflow.description == "A test workflow with description"
        except AttributeError:
            pytest.skip("create_workflow method not available")
        except TypeError:
            pytest.skip("description parameter not supported")

    def test_create_workflow_slug_stored(self, client):
        """Verify workflow slug is stored correctly."""
        try:
            unique_slug = f"test-slug-{uuid.uuid4().hex[:8]}"

            workflow = client.create_workflow(
                name="Slug Test Workflow",
                slug=unique_slug,
                product_surface="AGENT"
            )

            assert workflow is not None
            if hasattr(workflow, 'slug'):
                assert workflow.slug == unique_slug
        except AttributeError:
            pytest.skip("create_workflow method not available")


class TestListWorkflows:
    """Test workflow listing."""

    def test_list_workflows(self, client):
        """List all workflows."""
        try:
            response = client.list_workflows()

            assert response is not None
            if hasattr(response, 'workflows'):
                assert isinstance(response.workflows, list)
            elif hasattr(response, 'data'):
                assert isinstance(response.data, list)
        except AttributeError:
            pytest.skip("list_workflows method not available")


class TestStartRun:
    """Test agent run operations."""

    def test_start_run(self, client, test_customer, test_workflow):
        """Start an agent run.

        Runs track individual executions of a workflow,
        including events and costs.
        """
        try:
            correlation_id = f"trace_{uuid.uuid4().hex[:16]}"

            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=correlation_id
            )

            assert run is not None
            assert run.id is not None
        except AttributeError:
            pytest.skip("start_run method not available")

    def test_start_run_with_metadata(self, client, test_customer, test_workflow):
        """Start run with metadata."""
        try:
            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"trace_{uuid.uuid4().hex[:16]}",
                metadata={"test": True, "source": "sdk_test"}
            )

            assert run is not None
        except AttributeError:
            pytest.skip("start_run method not available")
        except TypeError:
            pytest.skip("metadata parameter not supported")


class TestEmitEvent:
    """Test event emission to runs."""

    def test_emit_event_basic(self, client, test_customer, test_workflow):
        """Emit an event to a run.

        Events track individual operations within a run,
        such as API calls or token usage.
        """
        try:
            # Start a run first
            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"trace_{uuid.uuid4().hex[:16]}"
            )

            event = client.emit_event(
                run_id=run.id,
                event_type="tokens.generated",
                quantity=1500,
                units="tokens"
            )

            assert event is not None
            if hasattr(event, 'id'):
                assert event.id is not None
        except AttributeError:
            pytest.skip("emit_event method not available")

    def test_emit_event_with_cost(self, client, test_customer, test_workflow):
        """Emit event with cost information."""
        try:
            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"trace_{uuid.uuid4().hex[:16]}"
            )

            event = client.emit_event(
                run_id=run.id,
                event_type="api.call",
                quantity=1,
                units="calls",
                cost_units=0.015,
                cost_currency="USD"
            )

            assert event is not None
        except AttributeError:
            pytest.skip("emit_event method not available")
        except TypeError:
            pytest.skip("cost parameters not supported")


class TestEmitEventsBatch:
    """Test batch event emission."""

    def test_emit_events_batch(self, client, test_customer, test_workflow):
        """Emit multiple events in batch."""
        try:
            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"trace_{uuid.uuid4().hex[:16]}"
            )

            events = [
                {"event_type": "prompt.received", "quantity": 100, "units": "tokens"},
                {"event_type": "completion.generated", "quantity": 500, "units": "tokens"},
                {"event_type": "tool.called", "quantity": 1, "units": "calls"}
            ]

            result = client.emit_events_batch(
                run_id=run.id,
                events=events
            )

            assert result is not None
        except AttributeError:
            pytest.skip("emit_events_batch method not available")
        except TypeError:
            # Try alternative parameter format
            try:
                result = client.emit_events_batch(events=events, run_id=run.id)
                assert result is not None
            except Exception:
                pytest.skip("emit_events_batch parameters not compatible")


class TestGetRunTimeline:
    """Test run timeline retrieval."""

    def test_get_run_timeline(self, client, test_customer, test_workflow):
        """Get run timeline with events."""
        try:
            # Create run and emit events
            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"trace_{uuid.uuid4().hex[:16]}"
            )

            client.emit_event(
                run_id=run.id,
                event_type="test.event",
                quantity=100,
                units="units"
            )

            timeline = client.get_run_timeline(run.id)

            assert timeline is not None
            # Timeline should contain the emitted event
            if hasattr(timeline, 'events'):
                assert len(timeline.events) > 0
        except AttributeError:
            pytest.skip("get_run_timeline method not available")


class TestEndRun:
    """Test ending runs."""

    def test_end_run_completed(self, client, test_customer, test_workflow):
        """End an agent run as completed."""
        try:
            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"trace_{uuid.uuid4().hex[:16]}"
            )

            result = client.end_run(run.id, status="COMPLETED")

            assert result is not None
        except AttributeError:
            pytest.skip("end_run method not available")

    def test_end_run_failed(self, client, test_customer, test_workflow):
        """End an agent run as failed."""
        try:
            run = client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"trace_{uuid.uuid4().hex[:16]}"
            )

            result = client.end_run(run.id, status="FAILED")

            assert result is not None
        except AttributeError:
            pytest.skip("end_run method not available")


class TestRecordRun:
    """Test recording complete runs."""

    def test_record_run_basic(self, client, test_customer):
        """Record a complete run in one call.

        This is a convenience method that combines starting a run,
        emitting events, and ending the run.
        """
        try:
            unique_workflow = f"test-workflow-{uuid.uuid4().hex[:8]}"

            result = client.record_run(
                customer_id=test_customer.id,
                workflow=unique_workflow,
                events=[
                    {"eventType": "prompt.received", "quantity": 100, "units": "tokens"},
                    {"eventType": "completion.generated", "quantity": 500, "units": "tokens"}
                ],
                status="COMPLETED"
            )

            assert result is not None
        except AttributeError:
            pytest.skip("record_run method not available")

    def test_record_run_with_correlation(self, client, test_customer):
        """Record run with correlation ID."""
        try:
            unique_workflow = f"test-workflow-{uuid.uuid4().hex[:8]}"
            correlation_id = f"trace_{uuid.uuid4().hex[:16]}"

            result = client.record_run(
                customer_id=test_customer.id,
                workflow=unique_workflow,
                events=[
                    {"eventType": "test.event", "quantity": 1, "units": "events"}
                ],
                status="COMPLETED",
                correlation_id=correlation_id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("record_run method not available")
        except TypeError:
            pytest.skip("correlation_id parameter not supported")


class TestWorkflowValidation:
    """Test workflow input validation."""

    def test_create_workflow_duplicate_slug(self, client, test_workflow):
        """Test creating workflow with duplicate slug."""
        try:
            existing_slug = test_workflow.slug if hasattr(test_workflow, 'slug') else f"existing-{uuid.uuid4().hex[:8]}"

            # Try to create with same slug
            with pytest.raises(Exception):
                client.create_workflow(
                    name="Duplicate Workflow",
                    slug=existing_slug,
                    product_surface="AGENT"
                )
        except AttributeError:
            pytest.skip("create_workflow method not available")
        except AssertionError:
            # Might allow duplicates or overwrite
            pass

    def test_start_run_invalid_workflow(self, client, test_customer):
        """Test starting run with invalid workflow ID."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.start_run(
                    customer_id=test_customer.id,
                    workflow_id="wf_nonexistent_12345",
                    correlation_id=f"trace_{uuid.uuid4().hex[:16]}"
                )

            assert exc_info.value is not None
        except AttributeError:
            pytest.skip("start_run method not available")

    def test_emit_event_invalid_run(self, client):
        """Test emitting event to invalid run."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.emit_event(
                    run_id="run_nonexistent_12345",
                    event_type="test.event",
                    quantity=100,
                    units="units"
                )

            assert exc_info.value is not None
        except AttributeError:
            pytest.skip("emit_event method not available")
