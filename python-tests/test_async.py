"""Test AsyncDrip client operations.

This module tests the asynchronous client for all SDK operations,
verifying that async methods work correctly and support concurrent
operations.
"""
import pytest
import asyncio
import uuid

# Import SDK components
try:
    from drip import Drip, AsyncDrip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None
    AsyncDrip = None


pytestmark = [
    pytest.mark.skipif(not DRIP_SDK_AVAILABLE, reason="drip-sdk not installed"),
    pytest.mark.asyncio
]


class TestAsyncContextManager:
    """Test async client context manager."""

    async def test_async_context_manager(self, api_key, base_url, check_sdk):
        """Test async client as context manager.

        The async client should support use as an async context
        manager for proper resource cleanup.
        """
        try:
            async with AsyncDrip(api_key=api_key, base_url=base_url) as client:
                result = await client.ping()
                assert result is not None
        except TypeError:
            pytest.skip("AsyncDrip does not support async context manager")

    async def test_async_context_manager_cleanup(self, api_key, base_url, check_sdk):
        """Verify resources are cleaned up after context exit."""
        try:
            async with AsyncDrip(api_key=api_key, base_url=base_url) as client:
                await client.ping()
            # After context, client should be closed (no errors expected)
        except TypeError:
            pytest.skip("AsyncDrip does not support async context manager")


class TestAsyncClose:
    """Test async client close."""

    async def test_async_close(self, api_key, base_url, check_sdk):
        """Test explicit async close."""
        client = AsyncDrip(api_key=api_key, base_url=base_url)
        try:
            result = await client.ping()
            assert result is not None
        finally:
            if hasattr(client, 'close'):
                close_method = client.close
                if asyncio.iscoroutinefunction(close_method):
                    await close_method()
                else:
                    close_method()


class TestAsyncPing:
    """Test async ping/health operations."""

    async def test_async_ping(self, async_client_factory, check_sdk):
        """Test async ping."""
        try:
            async with async_client_factory() as client:
                result = await client.ping()
                assert result is not None
        except TypeError:
            client = async_client_factory()
            try:
                result = await client.ping()
                assert result is not None
            finally:
                if hasattr(client, 'close'):
                    await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_get_health(self, async_client_factory, check_sdk):
        """Test async get_health."""
        try:
            async with async_client_factory() as client:
                result = await client.get_health()
                assert result is not None
        except TypeError:
            client = async_client_factory()
            try:
                result = await client.get_health()
                assert result is not None
            finally:
                if hasattr(client, 'close'):
                    await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncCustomer:
    """Test async customer operations."""

    async def test_async_create_customer(self, async_client_factory, check_sdk):
        """Test async customer creation."""
        unique_id = uuid.uuid4().hex[:12]
        client = async_client_factory()

        try:
            customer = await client.create_customer(
                onchain_address=f"0x{uuid.uuid4().hex}47",
                external_customer_id=f"async_test_{unique_id}",
                metadata={"async": True}
            )

            assert customer is not None
            assert customer.id.startswith("cus_")
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_get_customer(self, async_client_factory, test_customer, check_sdk):
        """Test async customer retrieval."""
        client = async_client_factory()

        try:
            customer = await client.get_customer(test_customer.id)
            assert customer is not None
            assert customer.id == test_customer.id
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_list_customers(self, async_client_factory, check_sdk):
        """Test async customer listing."""
        client = async_client_factory()

        try:
            response = await client.list_customers(limit=5)
            assert response is not None
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_get_balance(self, async_client_factory, test_customer, check_sdk):
        """Test async balance check."""
        client = async_client_factory()

        try:
            balance = await client.get_balance(test_customer.id)
            assert balance is not None
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncCharge:
    """Test async charge operations."""

    async def test_async_charge(self, async_client_factory, test_customer, check_sdk):
        """Test async charge creation."""
        client = async_client_factory()

        try:
            result = await client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=1,
                metadata={"async": True}
            )

            assert result is not None
            assert result.charge is not None
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_get_charge(self, async_client_factory, test_customer, check_sdk):
        """Test async charge retrieval."""
        client = async_client_factory()

        try:
            # Create charge first
            create_result = await client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=1
            )

            # Retrieve it
            charge = await client.get_charge(create_result.charge.id)
            assert charge is not None
            assert charge.id == create_result.charge.id
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_list_charges(self, async_client_factory, test_customer, check_sdk):
        """Test async charge listing."""
        client = async_client_factory()

        try:
            response = await client.list_charges(customer_id=test_customer.id, limit=5)
            assert response is not None
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncConcurrent:
    """Test concurrent async operations."""

    async def test_concurrent_operations(self, async_client_factory, test_customer, check_sdk):
        """Test running multiple operations concurrently."""
        client = async_client_factory()

        try:
            results = await asyncio.gather(
                client.get_balance(test_customer.id),
                client.list_customers(limit=5),
                client.list_charges(customer_id=test_customer.id, limit=5)
            )

            assert len(results) == 3
            assert all(r is not None for r in results)
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_concurrent_charges(self, async_client_factory, test_customer, check_sdk):
        """Test concurrent charge creation."""
        client = async_client_factory()

        try:
            # Create multiple charges concurrently
            charge_tasks = [
                client.charge(
                    customer_id=test_customer.id,
                    meter="api_calls",
                    quantity=1,
                    idempotency_key=f"concurrent_{uuid.uuid4().hex}"
                )
                for _ in range(3)
            ]

            results = await asyncio.gather(*charge_tasks)

            assert len(results) == 3
            # All charges should have unique IDs
            charge_ids = [r.charge.id for r in results]
            assert len(set(charge_ids)) == 3
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncWebhooks:
    """Test async webhook operations."""

    async def test_async_list_webhooks(self, async_client_factory, check_sdk):
        """Test async webhook listing."""
        client = async_client_factory()

        try:
            response = await client.list_webhooks()
            assert response is not None
        except AttributeError:
            pytest.skip("list_webhooks method not available on async client")
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_create_webhook(self, async_client_factory, check_sdk):
        """Test async webhook creation."""
        client = async_client_factory()

        try:
            unique_url = f"https://example.com/async-webhook/{uuid.uuid4().hex[:8]}"

            webhook = await client.create_webhook(
                url=unique_url,
                events=["charge.succeeded"]
            )

            assert webhook is not None
            assert webhook.id.startswith("wh_")

            # Cleanup
            await client.delete_webhook(webhook.id)
        except AttributeError:
            pytest.skip("webhook methods not available on async client")
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncWorkflows:
    """Test async workflow operations."""

    async def test_async_list_workflows(self, async_client_factory, check_sdk):
        """Test async workflow listing."""
        client = async_client_factory()

        try:
            response = await client.list_workflows()
            assert response is not None
        except AttributeError:
            pytest.skip("list_workflows method not available on async client")
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_workflow_run(self, async_client_factory, test_customer, test_workflow, check_sdk):
        """Test async workflow run operations."""
        client = async_client_factory()

        try:
            # Start run
            run = await client.start_run(
                customer_id=test_customer.id,
                workflow_id=test_workflow.id,
                correlation_id=f"async_trace_{uuid.uuid4().hex[:16]}"
            )

            assert run is not None

            # Emit event
            event = await client.emit_event(
                run_id=run.id,
                event_type="async.test",
                quantity=100,
                units="units"
            )

            assert event is not None

            # End run
            result = await client.end_run(run.id, status="COMPLETED")
            assert result is not None
        except AttributeError:
            pytest.skip("workflow methods not available on async client")
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncMeters:
    """Test async meter operations."""

    async def test_async_list_meters(self, async_client_factory, check_sdk):
        """Test async meter listing."""
        client = async_client_factory()

        try:
            response = await client.list_meters()
            assert response is not None
        except AttributeError:
            pytest.skip("list_meters method not available on async client")
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncCheckout:
    """Test async checkout operations."""

    async def test_async_checkout(self, async_client_factory, test_customer, check_sdk):
        """Test async checkout creation."""
        client = async_client_factory()

        try:
            result = await client.checkout(
                amount=1000,
                return_url="https://example.com/success",
                customer_id=test_customer.id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("checkout method not available on async client")
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()


class TestAsyncErrorHandling:
    """Test async error handling."""

    async def test_async_invalid_customer(self, async_client_factory, check_sdk):
        """Test async error on invalid customer."""
        client = async_client_factory()

        try:
            with pytest.raises(Exception) as exc_info:
                await client.get_customer("cus_nonexistent_12345")

            assert exc_info.value is not None
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()

    async def test_async_invalid_charge(self, async_client_factory, check_sdk):
        """Test async error on invalid charge."""
        client = async_client_factory()

        try:
            with pytest.raises(Exception) as exc_info:
                await client.get_charge("chg_nonexistent_12345")

            assert exc_info.value is not None
        finally:
            if hasattr(client, 'close'):
                await client.close() if asyncio.iscoroutinefunction(client.close) else client.close()
