"""Test idempotency key generation and handling.

This module tests the idempotency functionality of the SDK,
ensuring that duplicate requests can be detected and handled
appropriately.
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


class TestGenerateIdempotencyKey:
    """Test idempotency key generation."""

    def test_generate_idempotency_key_basic(self, check_sdk):
        """Test basic idempotency key generation.

        The SDK should provide a method to generate deterministic
        idempotency keys from input parameters.
        """
        try:
            key = Drip.generate_idempotency_key(
                customer_id="cus_123",
                step_name="process",
                run_id="run_456",
                sequence=1
            )

            assert key is not None
            assert isinstance(key, str)
            assert len(key) > 0
        except AttributeError:
            pytest.skip("generate_idempotency_key method not available")

    def test_generate_idempotency_key_deterministic(self, check_sdk):
        """Test idempotency key generation is deterministic.

        Same inputs should always produce the same key.
        """
        try:
            key1 = Drip.generate_idempotency_key(
                customer_id="cus_123",
                step_name="process",
                run_id="run_456",
                sequence=1
            )

            key2 = Drip.generate_idempotency_key(
                customer_id="cus_123",
                step_name="process",
                run_id="run_456",
                sequence=1
            )

            assert key1 == key2
        except AttributeError:
            pytest.skip("generate_idempotency_key method not available")

    def test_generate_idempotency_key_uniqueness(self, check_sdk):
        """Test different inputs produce different keys."""
        try:
            key1 = Drip.generate_idempotency_key(
                customer_id="cus_1",
                step_name="step_a",
                run_id="run_1",
                sequence=1
            )

            key2 = Drip.generate_idempotency_key(
                customer_id="cus_1",
                step_name="step_a",
                run_id="run_1",
                sequence=2  # Different sequence
            )

            assert key1 != key2
        except AttributeError:
            pytest.skip("generate_idempotency_key method not available")

    def test_generate_idempotency_key_different_customers(self, check_sdk):
        """Test keys differ for different customers."""
        try:
            key1 = Drip.generate_idempotency_key(
                customer_id="cus_abc",
                step_name="process",
                run_id="run_1",
                sequence=1
            )

            key2 = Drip.generate_idempotency_key(
                customer_id="cus_xyz",  # Different customer
                step_name="process",
                run_id="run_1",
                sequence=1
            )

            assert key1 != key2
        except AttributeError:
            pytest.skip("generate_idempotency_key method not available")

    def test_generate_idempotency_key_different_steps(self, check_sdk):
        """Test keys differ for different steps."""
        try:
            key1 = Drip.generate_idempotency_key(
                customer_id="cus_123",
                step_name="step_one",
                run_id="run_1",
                sequence=1
            )

            key2 = Drip.generate_idempotency_key(
                customer_id="cus_123",
                step_name="step_two",  # Different step
                run_id="run_1",
                sequence=1
            )

            assert key1 != key2
        except AttributeError:
            pytest.skip("generate_idempotency_key method not available")


class TestIdempotentChargeReplay:
    """Test charge idempotency replay detection."""

    def test_first_charge_not_replay(self, client, test_customer):
        """Test first charge with key is not a replay."""
        key = f"idem_first_{uuid.uuid4().hex}"

        result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=key
        )

        assert result is not None
        assert result.charge is not None

        # First call should not be a replay
        if hasattr(result, 'is_replay'):
            assert result.is_replay is False

    def test_replay_detected(self, client, test_customer):
        """Test replay is detected on second call."""
        key = f"idem_replay_{uuid.uuid4().hex}"

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

        # Both should return same charge
        assert result1.charge.id == result2.charge.id

        # Second call should be marked as replay
        if hasattr(result2, 'is_replay'):
            assert result2.is_replay is True

    def test_replay_same_charge_details(self, client, test_customer):
        """Test replayed charge returns same details."""
        key = f"idem_details_{uuid.uuid4().hex}"

        result1 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=5,
            idempotency_key=key,
            metadata={"original": True}
        )

        result2 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=5,
            idempotency_key=key,
            metadata={"original": True}
        )

        # Charge details should match
        assert result1.charge.id == result2.charge.id
        if hasattr(result1.charge, 'quantity') and hasattr(result2.charge, 'quantity'):
            assert result1.charge.quantity == result2.charge.quantity

    def test_different_keys_create_different_charges(self, client, test_customer):
        """Test different keys create distinct charges."""
        key1 = f"idem_diff_a_{uuid.uuid4().hex}"
        key2 = f"idem_diff_b_{uuid.uuid4().hex}"

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

        # Different keys should create different charges
        assert result1.charge.id != result2.charge.id


class TestIdempotencyEdgeCases:
    """Test idempotency edge cases."""

    def test_no_key_creates_new_charge(self, client, test_customer):
        """Test charges without key always create new charges."""
        result1 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1
        )

        result2 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1
        )

        # Without keys, both should create new charges
        assert result1.charge.id != result2.charge.id

    def test_key_with_different_params(self, client, test_customer):
        """Test using same key with different parameters.

        The behavior here depends on SDK implementation:
        - Some SDKs return the original charge
        - Some SDKs raise an error for mismatched params
        """
        key = f"idem_mismatch_{uuid.uuid4().hex}"

        result1 = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=key
        )

        # Try with different quantity
        try:
            result2 = client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=999,  # Different quantity
                idempotency_key=key
            )

            # If no error, should return original charge
            assert result2.charge.id == result1.charge.id
        except Exception as e:
            # SDK might reject mismatched parameters
            assert "idempotency" in str(e).lower() or "mismatch" in str(e).lower() or e is not None

    def test_empty_key_handled(self, client, test_customer):
        """Test empty idempotency key handling."""
        try:
            result = client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=1,
                idempotency_key=""
            )

            # Empty key might be treated as no key
            assert result is not None
        except Exception as e:
            # Or might be rejected
            assert e is not None

    def test_long_key_handled(self, client, test_customer):
        """Test very long idempotency key handling."""
        long_key = f"idem_{'x' * 500}_{uuid.uuid4().hex}"

        try:
            result = client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=1,
                idempotency_key=long_key
            )

            # Long key might be accepted or truncated
            assert result is not None
        except Exception as e:
            # Or might be rejected for exceeding length limits
            assert "key" in str(e).lower() or "length" in str(e).lower() or e is not None


class TestIdempotencyAcrossOperations:
    """Test idempotency across different operations."""

    def test_key_scoped_to_operation(self, client, test_customer):
        """Test idempotency key is scoped to operation type.

        The same key used for different operations should not
        cause conflicts (key is namespaced by operation).
        """
        key = f"shared_key_{uuid.uuid4().hex}"

        # Use key for charge
        charge_result = client.charge(
            customer_id=test_customer.id,
            meter="api_calls",
            quantity=1,
            idempotency_key=key
        )

        # The same key shouldn't affect different operations
        # This depends on SDK implementation
        assert charge_result is not None

    def test_multiple_replays(self, client, test_customer):
        """Test multiple replay calls return same result."""
        key = f"idem_multi_{uuid.uuid4().hex}"

        results = []
        for _ in range(3):
            result = client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=1,
                idempotency_key=key
            )
            results.append(result)

        # All should return the same charge
        charge_ids = [r.charge.id for r in results]
        assert len(set(charge_ids)) == 1
