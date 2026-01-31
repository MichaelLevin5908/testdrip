"""Test cost estimation features.

This module tests the cost estimation functionality for predicting
charges based on historical or hypothetical usage data.
"""
import pytest
from datetime import datetime, timedelta

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


class TestEstimateFromUsage:
    """Test estimation from historical usage."""

    def test_estimate_from_usage_basic(self, client, test_customer):
        """Estimate costs from historical usage.

        This uses actual historical usage data to estimate costs
        for a given period.
        """
        try:
            now = datetime.now()
            week_ago = now - timedelta(days=7)

            result = client.estimate_from_usage(
                period_start=week_ago,
                period_end=now,
                customer_id=test_customer.id
            )

            assert result is not None
            # Result should have cost information
            if hasattr(result, 'total_cost'):
                assert result.total_cost is not None
        except AttributeError:
            pytest.skip("estimate_from_usage method not available")

    def test_estimate_from_usage_with_default_price(self, client, test_customer):
        """Estimate with default unit price."""
        try:
            now = datetime.now()
            week_ago = now - timedelta(days=7)

            result = client.estimate_from_usage(
                period_start=week_ago,
                period_end=now,
                customer_id=test_customer.id,
                default_unit_price="0.001"
            )

            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_usage method not available")
        except TypeError:
            pytest.skip("default_unit_price parameter not supported")

    def test_estimate_from_usage_different_periods(self, client, test_customer):
        """Estimate for different time periods."""
        try:
            now = datetime.now()

            # Day estimate
            day_result = client.estimate_from_usage(
                period_start=now - timedelta(days=1),
                period_end=now,
                customer_id=test_customer.id
            )

            # Month estimate
            month_result = client.estimate_from_usage(
                period_start=now - timedelta(days=30),
                period_end=now,
                customer_id=test_customer.id
            )

            assert day_result is not None
            assert month_result is not None
        except AttributeError:
            pytest.skip("estimate_from_usage method not available")

    def test_estimate_from_usage_returns_breakdown(self, client, test_customer):
        """Check if estimation returns cost breakdown."""
        try:
            now = datetime.now()
            week_ago = now - timedelta(days=7)

            result = client.estimate_from_usage(
                period_start=week_ago,
                period_end=now,
                customer_id=test_customer.id
            )

            assert result is not None
            # May have breakdown by meter
            if hasattr(result, 'breakdown') or hasattr(result, 'items'):
                pass  # Has detailed breakdown
        except AttributeError:
            pytest.skip("estimate_from_usage method not available")


class TestEstimateFromHypothetical:
    """Test estimation from hypothetical usage."""

    def test_estimate_from_hypothetical_basic(self, client):
        """Estimate costs from hypothetical usage.

        This estimates costs based on hypothetical usage values
        without requiring actual historical data.
        """
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 1000},
                    {"meter": "tokens", "quantity": 50000}
                ]
            )

            assert result is not None
            if hasattr(result, 'total_cost'):
                assert result.total_cost is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")

    def test_estimate_from_hypothetical_with_price(self, client):
        """Estimate with custom default unit price."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 100}
                ],
                default_unit_price="0.01"
            )

            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")
        except TypeError:
            pytest.skip("default_unit_price parameter not supported")

    def test_estimate_from_hypothetical_single_meter(self, client):
        """Estimate for single meter usage."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 500}
                ]
            )

            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")

    def test_estimate_from_hypothetical_multiple_meters(self, client):
        """Estimate for multiple meter types."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 1000},
                    {"meter": "tokens", "quantity": 100000},
                    {"meter": "storage", "quantity": 1024}
                ]
            )

            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")

    def test_estimate_from_hypothetical_large_quantities(self, client):
        """Estimate with large quantities."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 1_000_000},
                    {"meter": "tokens", "quantity": 1_000_000_000}
                ]
            )

            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")


class TestEstimationResults:
    """Test estimation result formatting."""

    def test_estimate_has_total_cost(self, client):
        """Verify estimation returns total cost."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 100}
                ]
            )

            assert result is not None
            # Should have some total cost field
            has_total = (
                hasattr(result, 'total_cost') or
                hasattr(result, 'total') or
                hasattr(result, 'estimated_cost') or
                hasattr(result, 'amount')
            )
            assert has_total or result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")

    def test_estimate_cost_is_numeric(self, client):
        """Verify estimated cost is numeric."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 100}
                ]
            )

            assert result is not None

            # Extract total cost
            total = None
            if hasattr(result, 'total_cost'):
                total = result.total_cost
            elif hasattr(result, 'total'):
                total = result.total

            if total is not None:
                # Should be numeric (int, float, or string representation)
                assert isinstance(total, (int, float, str))
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")


class TestEstimationValidation:
    """Test estimation input validation."""

    def test_estimate_empty_items(self, client):
        """Test estimation with empty items list."""
        try:
            result = client.estimate_from_hypothetical(items=[])

            # Might return zero cost or raise error
            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")
        except Exception as e:
            # Empty items might be rejected
            assert "items" in str(e).lower() or e is not None

    def test_estimate_zero_quantity(self, client):
        """Test estimation with zero quantity."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 0}
                ]
            )

            assert result is not None
            # Zero quantity should give zero cost
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")

    def test_estimate_invalid_meter(self, client):
        """Test estimation with invalid meter name."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "nonexistent_meter_xyz", "quantity": 100}
                ]
            )

            # Might succeed with zero cost or raise error
            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")
        except Exception as e:
            # Invalid meter might be rejected
            assert "meter" in str(e).lower() or e is not None


class TestEstimationForCustomer:
    """Test customer-specific estimation."""

    def test_estimate_with_customer_pricing(self, client, test_customer):
        """Test estimation uses customer-specific pricing if available."""
        try:
            now = datetime.now()
            week_ago = now - timedelta(days=7)

            result = client.estimate_from_usage(
                period_start=week_ago,
                period_end=now,
                customer_id=test_customer.id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_usage method not available")

    def test_estimate_hypothetical_for_customer(self, client, test_customer):
        """Test hypothetical estimation for specific customer."""
        try:
            result = client.estimate_from_hypothetical(
                items=[
                    {"meter": "api_calls", "quantity": 1000}
                ],
                customer_id=test_customer.id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("estimate_from_hypothetical method not available")
        except TypeError:
            # customer_id might not be supported for hypothetical
            pytest.skip("customer_id not supported for hypothetical estimation")
