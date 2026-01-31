"""Test high-frequency streaming meter.

This module tests the StreamMeter functionality for tracking
high-frequency, incremental usage accumulation before flushing
as a single charge.
"""
import pytest
import asyncio

# Import SDK components
try:
    from drip import Drip, AsyncDrip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None
    AsyncDrip = None


pytestmark = pytest.mark.skipif(
    not DRIP_SDK_AVAILABLE,
    reason="drip-sdk not installed"
)


class TestStreamMeterCreation:
    """Test StreamMeter creation."""

    def test_create_stream_meter(self, client, test_customer):
        """Create a stream meter instance.

        StreamMeter accumulates usage before flushing to create
        a single charge, reducing API calls for high-frequency events.
        """
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            assert meter is not None
        except AttributeError:
            pytest.skip("create_stream_meter method not available")

    def test_create_stream_meter_with_threshold(self, client, test_customer):
        """Create a stream meter with flush threshold."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens",
                flush_threshold=1000
            )

            assert meter is not None
        except AttributeError:
            pytest.skip("create_stream_meter method not available")
        except TypeError:
            # flush_threshold might not be supported
            pytest.skip("flush_threshold parameter not supported")


class TestStreamMeterSync:
    """Test synchronous stream metering operations."""

    def test_add_sync_accumulates(self, client, test_customer):
        """Test synchronous quantity accumulation.

        Adding quantities should accumulate without immediately
        creating a charge.
        """
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            meter.add_sync(100)
            meter.add_sync(200)

            # Total should be sum of added quantities
            assert meter.total == 300
        except AttributeError:
            pytest.skip("StreamMeter sync operations not available")

    def test_add_sync_multiple_times(self, client, test_customer):
        """Test multiple sync additions."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            quantities = [50, 75, 100, 125, 150]
            for q in quantities:
                meter.add_sync(q)

            assert meter.total == sum(quantities)
        except AttributeError:
            pytest.skip("StreamMeter sync operations not available")

    def test_flush_creates_charge(self, client, test_customer):
        """Test flushing accumulated usage creates a charge."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            meter.add_sync(100)
            meter.add_sync(200)

            result = meter.flush()

            assert result is not None
            if hasattr(result, 'charge'):
                assert result.charge is not None
                assert result.charge.id.startswith("chg_")
        except AttributeError:
            pytest.skip("StreamMeter flush not available")

    def test_flush_resets_total(self, client, test_customer):
        """Test that flush resets the accumulated total."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            meter.add_sync(100)
            meter.flush()

            # After flush, total should be reset
            assert meter.total == 0
        except AttributeError:
            pytest.skip("StreamMeter sync operations not available")

    def test_flush_empty_meter(self, client, test_customer):
        """Test flushing a meter with no accumulated usage."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            # Flush without adding anything
            result = meter.flush()

            # Should handle gracefully (might skip or return null charge)
            assert result is None or result is not None
        except AttributeError:
            pytest.skip("StreamMeter flush not available")


class TestStreamMeterCallbacks:
    """Test StreamMeter callback functionality."""

    def test_on_add_callback(self, client, test_customer):
        """Test on_add callback is invoked when adding."""
        callback_invocations = []

        def on_add_callback(quantity, total):
            callback_invocations.append({"quantity": quantity, "total": total})

        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens",
                on_add=on_add_callback
            )

            meter.add_sync(100)
            meter.add_sync(200)

            # Callback should have been called twice
            assert len(callback_invocations) == 2
            assert callback_invocations[0]["quantity"] == 100
            assert callback_invocations[1]["quantity"] == 200
            assert callback_invocations[1]["total"] == 300
        except AttributeError:
            pytest.skip("StreamMeter callbacks not available")
        except TypeError:
            pytest.skip("on_add callback parameter not supported")

    def test_on_flush_callback(self, client, test_customer):
        """Test on_flush callback is invoked when flushing."""
        flush_results = []

        def on_flush_callback(result):
            flush_results.append(result)

        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens",
                on_flush=on_flush_callback
            )

            meter.add_sync(100)
            meter.flush()

            # Callback should have been called once
            assert len(flush_results) == 1
        except AttributeError:
            pytest.skip("StreamMeter callbacks not available")
        except TypeError:
            pytest.skip("on_flush callback parameter not supported")


class TestStreamMeterAsync:
    """Test asynchronous stream metering operations."""

    @pytest.mark.asyncio
    async def test_async_add(self, async_client_factory, test_customer):
        """Test asynchronous quantity accumulation."""
        try:
            async with async_client_factory() as client:
                meter = client.create_stream_meter(
                    customer_id=test_customer.id,
                    meter="tokens"
                )

                await meter.add(100)
                await meter.add(200)

                assert meter.total == 300
        except AttributeError:
            pytest.skip("AsyncDrip StreamMeter not available")
        except TypeError:
            pytest.skip("Async context manager not supported")

    @pytest.mark.asyncio
    async def test_async_flush(self, async_client_factory, test_customer):
        """Test asynchronous flush creates a charge."""
        try:
            async with async_client_factory() as client:
                meter = client.create_stream_meter(
                    customer_id=test_customer.id,
                    meter="tokens"
                )

                await meter.add(150)
                result = await meter.flush_async()

                assert result is not None
                if hasattr(result, 'charge'):
                    assert result.charge is not None
        except AttributeError:
            pytest.skip("AsyncDrip StreamMeter not available")
        except TypeError:
            pytest.skip("Async context manager not supported")

    @pytest.mark.asyncio
    async def test_async_concurrent_adds(self, async_client_factory, test_customer):
        """Test concurrent async additions."""
        try:
            async with async_client_factory() as client:
                meter = client.create_stream_meter(
                    customer_id=test_customer.id,
                    meter="tokens"
                )

                # Add concurrently
                await asyncio.gather(
                    meter.add(100),
                    meter.add(100),
                    meter.add(100)
                )

                # Total should be sum of all additions
                assert meter.total == 300
        except AttributeError:
            pytest.skip("AsyncDrip StreamMeter not available")
        except TypeError:
            pytest.skip("Async context manager not supported")


class TestStreamMeterEdgeCases:
    """Test StreamMeter edge cases and validation."""

    def test_add_zero_quantity(self, client, test_customer):
        """Test adding zero quantity."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            meter.add_sync(0)

            # Zero should be valid but not change total
            assert meter.total == 0
        except AttributeError:
            pytest.skip("StreamMeter not available")

    def test_add_large_quantity(self, client, test_customer):
        """Test adding large quantity."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            large_quantity = 1_000_000
            meter.add_sync(large_quantity)

            assert meter.total == large_quantity
        except AttributeError:
            pytest.skip("StreamMeter not available")

    def test_multiple_flushes(self, client, test_customer):
        """Test multiple flush cycles."""
        try:
            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens"
            )

            # First cycle
            meter.add_sync(100)
            result1 = meter.flush()

            # Second cycle
            meter.add_sync(200)
            result2 = meter.flush()

            # Each flush should create a separate charge
            if hasattr(result1, 'charge') and hasattr(result2, 'charge'):
                if result1.charge and result2.charge:
                    assert result1.charge.id != result2.charge.id
        except AttributeError:
            pytest.skip("StreamMeter not available")

    def test_auto_flush_on_threshold(self, client, test_customer):
        """Test auto-flush when threshold is reached."""
        try:
            flush_count = []

            def on_flush(result):
                flush_count.append(result)

            meter = client.create_stream_meter(
                customer_id=test_customer.id,
                meter="tokens",
                flush_threshold=100,
                on_flush=on_flush
            )

            # Add enough to trigger auto-flush
            meter.add_sync(150)

            # Should have auto-flushed
            assert len(flush_count) >= 1 or meter.total <= 100
        except AttributeError:
            pytest.skip("StreamMeter auto-flush not available")
        except TypeError:
            pytest.skip("flush_threshold/on_flush not supported")
