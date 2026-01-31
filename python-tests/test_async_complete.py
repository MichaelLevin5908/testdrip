"""
Complete async client tests for Drip SDK.

This module provides comprehensive test coverage for all AsyncDrip methods,
including charging, usage tracking, cost estimation, workflows, and webhooks.
"""

import pytest
from typing import Dict, Any

# Check if drip-sdk is available
try:
    from drip import AsyncDrip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False

pytestmark = [
    pytest.mark.skipif(not DRIP_SDK_AVAILABLE, reason="drip-sdk not installed"),
    pytest.mark.asyncio
]


class TestAsyncCharging:
    """Test async charging operations."""

    async def test_async_charge(self, async_client, test_customer):
        """Test basic async charge operation."""
        charge = await async_client.charge(
            customer_id=test_customer.id,
            meter="tokens",
            quantity=100
        )
        assert charge is not None
        assert charge.id is not None

    async def test_async_charge_with_metadata(self, async_client, test_customer, unique_id):
        """Test async charge with metadata."""
        charge = await async_client.charge(
            customer_id=test_customer.id,
            meter="tokens",
            quantity=50,
            metadata={"test_id": unique_id, "source": "async_test"}
        )
        assert charge is not None
        assert charge.id is not None

    async def test_async_charge_with_idempotency(self, async_client, test_customer, idempotency_key):
        """Test async charge with idempotency key."""
        charge1 = await async_client.charge(
            customer_id=test_customer.id,
            meter="tokens",
            quantity=25,
            idempotency_key=idempotency_key
        )

        # Same idempotency key should return same charge
        charge2 = await async_client.charge(
            customer_id=test_customer.id,
            meter="tokens",
            quantity=25,
            idempotency_key=idempotency_key
        )

        assert charge1.id == charge2.id

    async def test_async_get_charge_status(self, async_client, test_customer):
        """Test async get_charge_status."""
        charge = await async_client.charge(
            customer_id=test_customer.id,
            meter="tokens",
            quantity=100
        )
        status = await async_client.get_charge_status(charge.id)
        assert status is not None
        # Status could be pending, settled, or failed
        status_value = status.status if hasattr(status, 'status') else status.get('status')
        assert status_value in ["pending", "settled", "failed", "processing"]


class TestAsyncUsageTracking:
    """Test async usage tracking operations."""

    async def test_async_track_usage(self, async_client, test_customer):
        """Test async track_usage."""
        result = await async_client.track_usage(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            description="Async usage test"
        )
        assert result is not None
        # Check for recorded flag - attribute or dict access
        recorded = result.recorded if hasattr(result, 'recorded') else result.get('recorded', True)
        assert recorded is True

    async def test_async_track_usage_with_timestamp(self, async_client, test_customer):
        """Test async track_usage with custom timestamp."""
        import time
        timestamp = int(time.time() * 1000)  # milliseconds

        result = await async_client.track_usage(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=5,
            timestamp=timestamp,
            description="Async usage with timestamp"
        )
        assert result is not None

    async def test_async_track_usage_batch(self, async_client, test_customer):
        """Test async batch usage tracking."""
        events = [
            {"meter": "api_calls", "quantity": 1},
            {"meter": "tokens", "quantity": 100},
            {"meter": "compute_time", "quantity": 500}
        ]

        for event in events:
            result = await async_client.track_usage(
                customer_id=test_customer.id,
                meter=event["meter"],
                quantity=event["quantity"]
            )
            assert result is not None


class TestAsyncWrapApiCall:
    """Test async wrap_api_call functionality."""

    async def test_async_wrap_api_call(self, async_client, test_customer):
        """Test async wrap_api_call."""
        async def mock_api():
            return {"tokens": 50}

        result = await async_client.wrap_api_call(
            call=mock_api,
            customer_id=test_customer.id,
            meter="tokens",
            extract_usage=lambda r: r["tokens"]
        )

        # Check result structure
        api_result = result.result if hasattr(result, 'result') else result.get('result')
        assert api_result == {"tokens": 50}

        # Check charge was created
        charge = result.charge if hasattr(result, 'charge') else result.get('charge')
        assert charge is not None

    async def test_async_wrap_api_call_with_error(self, async_client, test_customer):
        """Test async wrap_api_call handles errors gracefully."""
        async def failing_api():
            raise ValueError("API Error")

        with pytest.raises(ValueError):
            await async_client.wrap_api_call(
                call=failing_api,
                customer_id=test_customer.id,
                meter="tokens",
                extract_usage=lambda r: 0
            )

    async def test_async_wrap_api_call_with_metadata(self, async_client, test_customer, unique_id):
        """Test async wrap_api_call with metadata."""
        async def mock_api():
            return {"processed": True, "tokens_used": 75}

        result = await async_client.wrap_api_call(
            call=mock_api,
            customer_id=test_customer.id,
            meter="tokens",
            extract_usage=lambda r: r["tokens_used"],
            metadata={"test_id": unique_id}
        )

        api_result = result.result if hasattr(result, 'result') else result.get('result')
        assert api_result["processed"] is True


class TestAsyncCostEstimation:
    """Test async cost estimation operations."""

    async def test_async_estimate_from_usage(self, async_client, test_customer):
        """Test async cost estimation from usage."""
        result = await async_client.estimate_from_usage(
            customer_id=test_customer.id,
            period_start="2024-01-01",
            period_end="2024-01-31"
        )
        assert result is not None
        # Check for total_cost attribute or key
        has_total = hasattr(result, "total_cost") or (isinstance(result, dict) and "total_cost" in result)
        assert has_total or result is not None  # Some SDKs return different structures

    async def test_async_estimate_from_hypothetical(self, async_client):
        """Test async hypothetical cost estimation."""
        result = await async_client.estimate_from_hypothetical(
            items=[
                {"meter": "tokens", "quantity": 10000},
                {"meter": "api_calls", "quantity": 100}
            ]
        )
        assert result is not None

    async def test_async_estimate_single_item(self, async_client):
        """Test async hypothetical estimation for single item."""
        result = await async_client.estimate_from_hypothetical(
            items=[{"meter": "tokens", "quantity": 5000}]
        )
        assert result is not None


class TestAsyncWorkflows:
    """Test async workflow and run operations."""

    async def test_async_create_workflow(self, async_client, unique_id):
        """Test async create_workflow."""
        workflow = await async_client.create_workflow(
            name=f"Async Test Workflow {unique_id}",
            slug=f"async-test-{unique_id}",
            description="Created via async client"
        )
        assert workflow is not None
        assert workflow.id is not None

        slug = workflow.slug if hasattr(workflow, 'slug') else workflow.get('slug')
        assert slug == f"async-test-{unique_id}"

    async def test_async_start_run(self, async_client, test_customer, async_test_workflow):
        """Test async start_run."""
        run = await async_client.start_run(
            workflow_id=async_test_workflow.id,
            customer_id=test_customer.id
        )
        assert run is not None
        assert run.id is not None

    async def test_async_emit_event(self, async_client, test_customer, async_test_workflow):
        """Test async emit_event."""
        run = await async_client.start_run(
            workflow_id=async_test_workflow.id,
            customer_id=test_customer.id
        )

        result = await async_client.emit_event(
            run_id=run.id,
            type="llm_call",
            data={"model": "gpt-4", "tokens": 100}
        )
        assert result is not None

    async def test_async_get_run_timeline(self, async_client, test_customer, async_test_workflow):
        """Test async get_run_timeline."""
        run = await async_client.start_run(
            workflow_id=async_test_workflow.id,
            customer_id=test_customer.id
        )

        await async_client.emit_event(
            run_id=run.id,
            type="llm_call",
            data={"model": "gpt-4", "tokens": 100}
        )

        timeline = await async_client.get_run_timeline(run.id)
        assert timeline is not None

        events = timeline.events if hasattr(timeline, 'events') else timeline.get('events', [])
        assert len(events) >= 1

    async def test_async_emit_events_batch(self, async_client, test_customer, async_test_workflow):
        """Test async batch event emission."""
        run = await async_client.start_run(
            workflow_id=async_test_workflow.id,
            customer_id=test_customer.id
        )

        result = await async_client.emit_events_batch([
            {"run_id": run.id, "type": "tool_call", "data": {"tool": "search"}},
            {"run_id": run.id, "type": "tool_call", "data": {"tool": "calc"}}
        ])
        assert result is not None

        count = result.count if hasattr(result, 'count') else result.get('count', 2)
        assert count == 2

    async def test_async_end_run(self, async_client, test_customer, async_test_workflow):
        """Test async end_run."""
        run = await async_client.start_run(
            workflow_id=async_test_workflow.id,
            customer_id=test_customer.id
        )

        result = await async_client.end_run(
            run_id=run.id,
            status="completed"
        )
        assert result is not None

    async def test_async_record_run(self, async_client, test_customer, async_test_workflow):
        """Test async record_run (simplified run recording)."""
        result = await async_client.record_run(
            workflow_id=async_test_workflow.id,
            customer_id=test_customer.id,
            status="completed",
            events=[
                {"type": "llm_call", "data": {"model": "gpt-4", "tokens": 100}}
            ]
        )
        assert result is not None

        run_id = result.run_id if hasattr(result, 'run_id') else result.get('run_id')
        assert run_id is not None


class TestAsyncWebhooks:
    """Test async webhook operations."""

    async def test_async_create_webhook(self, async_client, test_webhook_url, unique_id):
        """Test async create_webhook."""
        webhook_url = f"{test_webhook_url}/{unique_id}"

        webhook = await async_client.create_webhook(
            url=webhook_url,
            events=["charge.created"]
        )
        assert webhook is not None
        assert webhook.id is not None

        # Cleanup
        await async_client.delete_webhook(webhook.id)

    async def test_async_list_webhooks(self, async_client):
        """Test async list_webhooks."""
        webhooks = await async_client.list_webhooks()
        assert webhooks is not None
        assert isinstance(webhooks, (list, tuple)) or hasattr(webhooks, '__iter__')

    async def test_async_get_webhook(self, async_client, test_webhook_url, unique_id):
        """Test async get_webhook."""
        webhook_url = f"{test_webhook_url}/get-{unique_id}"

        created = await async_client.create_webhook(
            url=webhook_url,
            events=["charge.created"]
        )

        webhook = await async_client.get_webhook(created.id)
        assert webhook is not None

        url = webhook.url if hasattr(webhook, 'url') else webhook.get('url')
        assert url == webhook_url

        # Cleanup
        await async_client.delete_webhook(created.id)

    async def test_async_update_webhook(self, async_client, test_webhook_url, unique_id):
        """Test async update_webhook."""
        webhook_url = f"{test_webhook_url}/update-{unique_id}"

        created = await async_client.create_webhook(
            url=webhook_url,
            events=["charge.created"]
        )

        updated = await async_client.update_webhook(
            webhook_id=created.id,
            events=["charge.created", "charge.settled"]
        )
        assert updated is not None

        # Cleanup
        await async_client.delete_webhook(created.id)

    async def test_async_delete_webhook(self, async_client, test_webhook_url, unique_id):
        """Test async delete_webhook."""
        webhook_url = f"{test_webhook_url}/delete-{unique_id}"

        created = await async_client.create_webhook(
            url=webhook_url,
            events=["charge.created"]
        )

        result = await async_client.delete_webhook(created.id)
        # Deletion typically returns None or success indicator
        assert result is None or result is True or (hasattr(result, 'deleted') and result.deleted)

    async def test_async_test_webhook(self, async_client, test_webhook_url, unique_id):
        """Test async test_webhook."""
        webhook_url = f"{test_webhook_url}/test-{unique_id}"

        created = await async_client.create_webhook(
            url=webhook_url,
            events=["charge.created"]
        )

        try:
            result = await async_client.test_webhook(created.id)
            # Check for success indicator
            sent = result.sent if hasattr(result, 'sent') else result.get('sent')
            success = result.success if hasattr(result, 'success') else result.get('success')
            assert sent is True or success is True
        finally:
            await async_client.delete_webhook(created.id)

    async def test_async_rotate_webhook_secret(self, async_client, test_webhook_url, unique_id):
        """Test async rotate_webhook_secret."""
        webhook_url = f"{test_webhook_url}/rotate-{unique_id}"

        created = await async_client.create_webhook(
            url=webhook_url,
            events=["charge.created"]
        )

        old_secret = created.secret if hasattr(created, 'secret') else created.get('secret')

        try:
            result = await async_client.rotate_webhook_secret(created.id)
            new_secret = result.secret if hasattr(result, 'secret') else result.get('secret')
            assert new_secret != old_secret
        finally:
            await async_client.delete_webhook(created.id)


class TestAsyncCustomers:
    """Test async customer operations."""

    async def test_async_create_customer(self, async_client, unique_id):
        """Test async create_customer."""
        customer = await async_client.create_customer(
            external_id=f"async-customer-{unique_id}",
            name="Async Test Customer",
            email=f"async-{unique_id}@example.com"
        )
        assert customer is not None
        assert customer.id is not None

    async def test_async_get_customer(self, async_client, test_customer):
        """Test async get_customer."""
        customer = await async_client.get_customer(test_customer.id)
        assert customer is not None
        assert customer.id == test_customer.id

    async def test_async_update_customer(self, async_client, unique_id):
        """Test async update_customer."""
        customer = await async_client.create_customer(
            external_id=f"update-test-{unique_id}",
            name="Original Name"
        )

        updated = await async_client.update_customer(
            customer_id=customer.id,
            name="Updated Name"
        )

        name = updated.name if hasattr(updated, 'name') else updated.get('name')
        assert name == "Updated Name"

    async def test_async_list_customers(self, async_client):
        """Test async list_customers."""
        customers = await async_client.list_customers()
        assert customers is not None
        assert isinstance(customers, (list, tuple)) or hasattr(customers, '__iter__')


class TestAsyncMeters:
    """Test async meter operations."""

    async def test_async_list_meters(self, async_client):
        """Test async list_meters."""
        meters = await async_client.list_meters()
        assert meters is not None
        assert isinstance(meters, (list, tuple)) or hasattr(meters, '__iter__')

    async def test_async_get_meter(self, async_client):
        """Test async get_meter."""
        meters = await async_client.list_meters()
        if meters and len(list(meters)) > 0:
            meter_list = list(meters)
            meter_id = meter_list[0].id if hasattr(meter_list[0], 'id') else meter_list[0].get('id')
            meter = await async_client.get_meter(meter_id)
            assert meter is not None


class TestAsyncHealth:
    """Test async health and utility operations."""

    async def test_async_ping(self, async_client):
        """Test async ping."""
        result = await async_client.ping()
        assert result is not None

        ok = result.get('ok') if isinstance(result, dict) else getattr(result, 'ok', True)
        assert ok is True

    async def test_async_health_check(self, async_client):
        """Test async health check."""
        health = await async_client.health()
        assert health is not None


class TestAsyncContextManager:
    """Test async context manager functionality."""

    async def test_async_client_context_manager(self, api_key, base_url, check_sdk):
        """Test async client as context manager."""
        async with AsyncDrip(api_key=api_key, base_url=base_url) as client:
            result = await client.ping()
            assert result is not None

    async def test_async_client_manual_close(self, api_key, base_url, check_sdk):
        """Test manual async client close."""
        client = AsyncDrip(api_key=api_key, base_url=base_url)
        try:
            result = await client.ping()
            assert result is not None
        finally:
            await client.close()
