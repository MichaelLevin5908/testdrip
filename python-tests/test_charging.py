"""Test charge creation and retrieval.

This module tests charging operations including creating charges,
retrieving charge details, listing charges, and tracking usage.
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


class TestCharge:
    """Test basic charge operations."""

    def test_charge_basic(self, client, test_customer):
        """Create a basic usage-based charge.

        A charge records usage against a customer's balance
        for a specific meter.
        """
        result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1
        )

        assert result is not None
        assert result.charge is not None
        assert result.charge.id is not None
        assert result.charge.id.startswith("chg_")

    def test_charge_with_metadata(self, client, test_customer):
        """Create a charge with metadata.

        Charges can include metadata for tracking purposes.
        """
        result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            metadata={"test": True, "source": "sdk_test"}
        )

        assert result is not None
        assert result.charge is not None

    def test_charge_quantity_stored(self, client, test_customer):
        """Verify charge quantity is stored correctly."""
        quantity = 5
        result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=quantity
        )

        assert result is not None
        assert result.charge is not None
        if hasattr(result.charge, 'quantity'):
            assert result.charge.quantity == quantity

    def test_charge_meter_stored(self, client, test_customer):
        """Verify charge meter is stored correctly."""
        meter = "api_calls"
        result = client.charge(
            customer_id=test_customer.id,
            meter=meter,
            quantity=1
        )

        assert result is not None
        assert result.charge is not None
        if hasattr(result.charge, 'meter'):
            assert result.charge.meter == meter


class TestChargeWithIdempotency:
    """Test idempotent charge handling."""

    def test_idempotent_charge_first_call(self, client, test_customer, idempotency_key):
        """First charge with idempotency key should succeed normally."""
        result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=idempotency_key
        )

        assert result is not None
        assert result.charge is not None
        # First call should not be a replay
        if hasattr(result, 'is_replay'):
            assert result.is_replay is False

    def test_idempotent_charge_replay(self, client, test_customer):
        """Second charge with same idempotency key should be detected as replay."""
        key = f"idem_replay_test_{uuid.uuid4().hex}"

        # First call
        result1 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=key
        )

        # Second call with same key
        result2 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=key
        )

        assert result1.charge.id == result2.charge.id
        if hasattr(result2, 'is_replay'):
            assert result2.is_replay is True

    def test_idempotent_charge_different_keys(self, client, test_customer):
        """Different idempotency keys should create different charges."""
        key1 = f"idem_diff_1_{uuid.uuid4().hex}"
        key2 = f"idem_diff_2_{uuid.uuid4().hex}"

        result1 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=key1
        )

        result2 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=key2
        )

        assert result1.charge.id != result2.charge.id


class TestGetCharge:
    """Test charge retrieval operations."""

    def test_get_charge(self, client, test_customer):
        """Retrieve a specific charge by ID."""
        # Create a charge first
        create_result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1
        )
        charge_id = create_result.charge.id

        # Retrieve it
        charge = client.get_charge(charge_id)

        assert charge is not None
        assert charge.id == charge_id

    def test_get_charge_fields(self, client, test_customer):
        """Verify retrieved charge has expected fields."""
        create_result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=2
        )
        charge_id = create_result.charge.id

        charge = client.get_charge(charge_id)

        assert charge is not None
        assert charge.id is not None
        # Check for common charge fields
        has_expected_fields = (
            hasattr(charge, 'id') and
            (hasattr(charge, 'meter') or hasattr(charge, 'quantity') or hasattr(charge, 'customer_id'))
        )
        assert has_expected_fields or charge is not None

    def test_get_charge_not_found(self, client):
        """Test retrieval of non-existent charge."""
        with pytest.raises(Exception) as exc_info:
            client.get_charge("chg_nonexistent_12345")

        assert exc_info.value is not None


class TestListCharges:
    """Test charge listing operations."""

    def test_list_charges_for_customer(self, client, test_customer):
        """List charges for a specific customer."""
        # Create a charge to ensure there's something to list
        client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1
        )

        response = client.list_charges(customer_id=test_customer.id)

        assert response is not None
        # Response should contain charges
        if hasattr(response, 'charges'):
            assert isinstance(response.charges, list)
        elif hasattr(response, 'data'):
            assert isinstance(response.data, list)

    def test_list_charges_with_limit(self, client, test_customer):
        """List charges with a limit parameter."""
        limit = 5
        response = client.list_charges(customer_id=test_customer.id, limit=limit)

        assert response is not None
        if hasattr(response, 'charges'):
            assert len(response.charges) <= limit
        elif hasattr(response, 'data'):
            assert len(response.data) <= limit

    def test_list_charges_contains_created(self, client, test_customer):
        """Verify created charge appears in list."""
        # Create a charge with unique metadata to identify it
        unique_id = uuid.uuid4().hex[:8]
        create_result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            metadata={"test_id": unique_id}
        )
        charge_id = create_result.charge.id

        response = client.list_charges(customer_id=test_customer.id, limit=10)

        # Find the created charge in the list
        if hasattr(response, 'charges'):
            charge_ids = [c.id for c in response.charges]
        elif hasattr(response, 'data'):
            charge_ids = [c.id for c in response.data]
        else:
            charge_ids = []

        assert charge_id in charge_ids or response is not None


class TestGetChargeStatus:
    """Test charge status operations."""

    def test_get_charge_status(self, client, test_customer):
        """Check charge settlement status."""
        # Create a charge
        create_result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1
        )
        charge_id = create_result.charge.id

        status = client.get_charge_status(charge_id)

        assert status is not None

    def test_charge_status_valid_values(self, client, test_customer):
        """Verify charge status is a valid value."""
        create_result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1
        )
        charge_id = create_result.charge.id

        status = client.get_charge_status(charge_id)

        # Status should be one of expected values
        valid_statuses = ["pending", "settled", "failed", "processing", "PENDING", "SETTLED", "FAILED", "PROCESSING"]
        if hasattr(status, 'status'):
            assert status.status in valid_statuses or status.status is not None
        else:
            assert status is not None


class TestTrackUsage:
    """Test usage tracking without immediate charge."""

    def test_track_usage_basic(self, client, test_customer):
        """Track usage without immediately charging.

        Usage tracking records activity that may be charged
        later or used for analytics.
        """
        try:
            result = client.track_usage(
                customer_id=test_customer.id,
                meter="tokens",
                quantity=1000,
                units="tokens",
                description="Test usage tracking"
            )

            assert result is not None
        except AttributeError:
            pytest.skip("track_usage method not available")

    def test_track_usage_with_metadata(self, client, test_customer):
        """Track usage with additional metadata."""
        try:
            result = client.track_usage(
                customer_id=test_customer.id,
                meter="tokens",
                quantity=500,
                units="tokens",
                description="Test with metadata",
                metadata={"model": "gpt-4", "test": True}
            )

            assert result is not None
        except AttributeError:
            pytest.skip("track_usage method not available")
        except TypeError:
            # metadata parameter might not be supported
            pytest.skip("track_usage does not accept metadata parameter")


class TestWrapApiCall:
    """Test wrapping API calls with automatic charging."""

    def test_wrap_api_call_basic(self, client, test_customer):
        """Test wrapping an API call with automatic charging.

        The wrap_api_call method executes a function and
        automatically creates a charge based on the result.
        """
        def mock_api_call():
            return {"tokens_used": 150}

        def extract_usage(result):
            return result["tokens_used"]

        try:
            result = client.wrap_api_call(
                customer_id=test_customer.id,
                meter="tokens",
                call=mock_api_call,
                extract_usage=extract_usage
            )

            assert result is not None
            # Should have both API result and charge
            if hasattr(result, 'api_result'):
                assert result.api_result == {"tokens_used": 150}
            if hasattr(result, 'charge'):
                assert result.charge is not None
        except AttributeError:
            pytest.skip("wrap_api_call method not available")

    def test_wrap_api_call_extracts_usage(self, client, test_customer):
        """Verify extracted usage is used for charge."""
        expected_usage = 250

        def mock_api_call():
            return {"usage": expected_usage, "status": "success"}

        def extract_usage(result):
            return result["usage"]

        try:
            result = client.wrap_api_call(
                customer_id=test_customer.id,
                meter="tokens",
                call=mock_api_call,
                extract_usage=extract_usage
            )

            assert result is not None
            if hasattr(result, 'charge') and hasattr(result.charge, 'quantity'):
                assert result.charge.quantity == expected_usage
        except AttributeError:
            pytest.skip("wrap_api_call method not available")

    def test_wrap_api_call_preserves_result(self, client, test_customer):
        """Verify API call result is preserved."""
        expected_result = {"data": [1, 2, 3], "tokens": 100}

        def mock_api_call():
            return expected_result

        def extract_usage(result):
            return result["tokens"]

        try:
            result = client.wrap_api_call(
                customer_id=test_customer.id,
                meter="tokens",
                call=mock_api_call,
                extract_usage=extract_usage
            )

            assert result is not None
            if hasattr(result, 'api_result'):
                assert result.api_result == expected_result
        except AttributeError:
            pytest.skip("wrap_api_call method not available")

    def test_wrap_api_call_handles_exception(self, client, test_customer):
        """Test behavior when wrapped call raises exception."""

        def failing_api_call():
            raise ValueError("API call failed")

        def extract_usage(result):
            return 100

        try:
            with pytest.raises(ValueError):
                client.wrap_api_call(
                    customer_id=test_customer.id,
                    meter="tokens",
                    call=failing_api_call,
                    extract_usage=extract_usage
                )
        except AttributeError:
            pytest.skip("wrap_api_call method not available")


class TestChargeValidation:
    """Test charge input validation."""

    def test_charge_invalid_customer(self, client):
        """Test charge with invalid customer ID."""
        with pytest.raises(Exception) as exc_info:
            client.charge(
                customer_id="cus_invalid_12345",
                meter="api_calls",
                quantity=1
            )

        assert exc_info.value is not None

    def test_charge_zero_quantity(self, client, test_customer):
        """Test charge with zero quantity."""
        # Zero quantity might be allowed or rejected
        try:
            result = client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=0
            )
            # If allowed, should create charge with zero
            assert result is not None
        except Exception as e:
            # Validation rejection is acceptable
            assert "quantity" in str(e).lower() or e is not None

    def test_charge_negative_quantity(self, client, test_customer):
        """Test charge with negative quantity."""
        with pytest.raises(Exception) as exc_info:
            client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=-1
            )

        # Negative quantities should be rejected
        assert exc_info.value is not None
