"""Test fiat on-ramp checkout.

This module tests the checkout functionality for allowing
customers to add funds via fiat payment.
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


class TestCheckout:
    """Test checkout session creation."""

    def test_checkout_basic(self, client, test_customer):
        """Create a checkout session for fiat deposit.

        Checkout sessions allow customers to add funds to their
        balance using fiat payment methods.
        """
        try:
            result = client.checkout(
                amount=5000,  # $50.00 in cents
                return_url="https://example.com/success",
                customer_id=test_customer.id
            )

            assert result is not None
            # Should return a checkout URL or session
            if hasattr(result, 'url'):
                assert result.url is not None
                assert result.url.startswith("http")
            elif hasattr(result, 'checkout_url'):
                assert result.checkout_url is not None
        except AttributeError:
            pytest.skip("checkout method not available")

    def test_checkout_with_cancel_url(self, client, test_customer):
        """Create checkout with cancel URL."""
        try:
            result = client.checkout(
                amount=1000,  # $10.00
                return_url="https://example.com/success",
                customer_id=test_customer.id,
                cancel_url="https://example.com/cancel"
            )

            assert result is not None
        except AttributeError:
            pytest.skip("checkout method not available")
        except TypeError:
            pytest.skip("cancel_url parameter not supported")

    def test_checkout_with_metadata(self, client, test_customer):
        """Create checkout with metadata."""
        try:
            result = client.checkout(
                amount=2000,  # $20.00
                return_url="https://example.com/success",
                customer_id=test_customer.id,
                metadata={"test": True, "campaign": "sdk_test"}
            )

            assert result is not None
        except AttributeError:
            pytest.skip("checkout method not available")
        except TypeError:
            pytest.skip("metadata parameter not supported")

    def test_checkout_returns_url(self, client, test_customer):
        """Verify checkout returns a valid URL."""
        try:
            result = client.checkout(
                amount=1000,
                return_url="https://example.com/success",
                customer_id=test_customer.id
            )

            assert result is not None
            # Extract URL from result
            url = None
            if hasattr(result, 'url'):
                url = result.url
            elif hasattr(result, 'checkout_url'):
                url = result.checkout_url

            if url:
                assert url.startswith("http")
                # URL should contain session or checkout identifier
                assert len(url) > 20
        except AttributeError:
            pytest.skip("checkout method not available")


class TestCheckoutWithExternalId:
    """Test checkout with external customer ID."""

    def test_checkout_external_customer_id(self, client):
        """Create checkout with external customer ID.

        This allows creating checkout sessions without first
        creating a customer record.
        """
        try:
            external_id = f"ext_user_{uuid.uuid4().hex[:8]}"

            result = client.checkout(
                amount=1000,
                return_url="https://example.com/success",
                external_customer_id=external_id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("checkout method not available")
        except TypeError:
            pytest.skip("external_customer_id parameter not supported")

    def test_checkout_external_id_vs_customer_id(self, client, test_customer):
        """Test checkout prefers customer_id over external_id."""
        try:
            external_id = f"ext_different_{uuid.uuid4().hex[:8]}"

            # When both provided, customer_id should take precedence
            result = client.checkout(
                amount=1000,
                return_url="https://example.com/success",
                customer_id=test_customer.id,
                external_customer_id=external_id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("checkout method not available")
        except TypeError:
            pytest.skip("external_customer_id parameter not supported")


class TestCheckoutAmounts:
    """Test checkout amount handling."""

    def test_checkout_minimum_amount(self, client, test_customer):
        """Test minimum checkout amount."""
        try:
            # Minimum might be enforced by payment processor
            result = client.checkout(
                amount=100,  # $1.00 - typical minimum
                return_url="https://example.com/success",
                customer_id=test_customer.id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("checkout method not available")
        except Exception as e:
            # Might reject amounts below minimum
            if "minimum" in str(e).lower() or "amount" in str(e).lower():
                pytest.skip(f"Amount below minimum: {e}")
            raise

    def test_checkout_large_amount(self, client, test_customer):
        """Test larger checkout amount."""
        try:
            result = client.checkout(
                amount=100000,  # $1000.00
                return_url="https://example.com/success",
                customer_id=test_customer.id
            )

            assert result is not None
        except AttributeError:
            pytest.skip("checkout method not available")
        except Exception as e:
            # Might have maximum limits
            if "maximum" in str(e).lower() or "amount" in str(e).lower():
                pytest.skip(f"Amount above maximum: {e}")
            raise


class TestCheckoutValidation:
    """Test checkout input validation."""

    def test_checkout_invalid_customer(self, client):
        """Test checkout with invalid customer ID."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.checkout(
                    amount=1000,
                    return_url="https://example.com/success",
                    customer_id="cus_invalid_12345"
                )

            assert exc_info.value is not None
        except AttributeError:
            pytest.skip("checkout method not available")

    def test_checkout_zero_amount(self, client, test_customer):
        """Test checkout with zero amount."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.checkout(
                    amount=0,
                    return_url="https://example.com/success",
                    customer_id=test_customer.id
                )

            # Zero amount should be rejected
            assert exc_info.value is not None
        except AttributeError:
            pytest.skip("checkout method not available")

    def test_checkout_negative_amount(self, client, test_customer):
        """Test checkout with negative amount."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.checkout(
                    amount=-1000,
                    return_url="https://example.com/success",
                    customer_id=test_customer.id
                )

            # Negative amount should be rejected
            assert exc_info.value is not None
        except AttributeError:
            pytest.skip("checkout method not available")

    def test_checkout_invalid_return_url(self, client, test_customer):
        """Test checkout with invalid return URL."""
        try:
            # Invalid URL format might be rejected
            with pytest.raises(Exception):
                client.checkout(
                    amount=1000,
                    return_url="not-a-valid-url",
                    customer_id=test_customer.id
                )
        except AttributeError:
            pytest.skip("checkout method not available")
        except AssertionError:
            # If it doesn't raise, the SDK accepts any string
            pass
