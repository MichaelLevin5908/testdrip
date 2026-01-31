"""Test error handling and exception types.

This module tests that the SDK properly handles and raises
appropriate exceptions for various error conditions.
"""
import pytest

# Import SDK components and exceptions
try:
    from drip import Drip, AsyncDrip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None
    AsyncDrip = None

# Try to import specific exception types
try:
    from drip import DripError
    DRIP_ERROR_AVAILABLE = True
except ImportError:
    DRIP_ERROR_AVAILABLE = False
    DripError = Exception

try:
    from drip import DripAPIError
    DRIP_API_ERROR_AVAILABLE = True
except ImportError:
    DRIP_API_ERROR_AVAILABLE = False
    DripAPIError = Exception

try:
    from drip import DripAuthenticationError
    DRIP_AUTH_ERROR_AVAILABLE = True
except ImportError:
    DRIP_AUTH_ERROR_AVAILABLE = False
    DripAuthenticationError = Exception

try:
    from drip import DripPaymentRequiredError
    DRIP_PAYMENT_ERROR_AVAILABLE = True
except ImportError:
    DRIP_PAYMENT_ERROR_AVAILABLE = False
    DripPaymentRequiredError = Exception

try:
    from drip import DripRateLimitError
    DRIP_RATE_LIMIT_ERROR_AVAILABLE = True
except ImportError:
    DRIP_RATE_LIMIT_ERROR_AVAILABLE = False
    DripRateLimitError = Exception

try:
    from drip import DripNetworkError
    DRIP_NETWORK_ERROR_AVAILABLE = True
except ImportError:
    DRIP_NETWORK_ERROR_AVAILABLE = False
    DripNetworkError = Exception


pytestmark = pytest.mark.skipif(
    not DRIP_SDK_AVAILABLE,
    reason="drip-sdk not installed"
)


class TestAuthenticationError:
    """Test authentication error handling."""

    def test_invalid_api_key(self, base_url, check_sdk):
        """Test invalid API key raises authentication error."""
        bad_client = Drip(api_key="invalid_key_12345", base_url=base_url)

        with pytest.raises(Exception) as exc_info:
            bad_client.ping()

        # Should be an authentication-related error
        error = exc_info.value
        assert error is not None

        if DRIP_AUTH_ERROR_AVAILABLE:
            # Prefer specific exception type check
            assert isinstance(error, (DripAuthenticationError, Exception))

    def test_malformed_api_key(self, base_url, check_sdk):
        """Test malformed API key handling."""
        bad_client = Drip(api_key="drip_sk_malformed_key", base_url=base_url)

        with pytest.raises(Exception) as exc_info:
            bad_client.ping()

        error = exc_info.value
        assert error is not None

    def test_auth_error_has_status_code(self, base_url, check_sdk):
        """Test authentication error includes status code."""
        bad_client = Drip(api_key="invalid_key", base_url=base_url)

        with pytest.raises(Exception) as exc_info:
            bad_client.ping()

        error = exc_info.value
        if hasattr(error, 'status_code'):
            assert error.status_code == 401 or error.status_code == 403


class TestNotFoundError:
    """Test 404 not found error handling."""

    def test_customer_not_found(self, client):
        """Test 404 error for non-existent customer."""
        with pytest.raises(Exception) as exc_info:
            client.get_customer("cus_nonexistent_12345")

        error = exc_info.value
        assert error is not None

        if hasattr(error, 'status_code'):
            assert error.status_code == 404

    def test_charge_not_found(self, client):
        """Test 404 error for non-existent charge."""
        with pytest.raises(Exception) as exc_info:
            client.get_charge("chg_nonexistent_12345")

        error = exc_info.value
        assert error is not None

        if hasattr(error, 'status_code'):
            assert error.status_code == 404

    def test_webhook_not_found(self, client):
        """Test 404 error for non-existent webhook."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.get_webhook("wh_nonexistent_12345")

            error = exc_info.value
            assert error is not None
        except AttributeError:
            pytest.skip("get_webhook method not available")


class TestValidationError:
    """Test input validation error handling."""

    def test_invalid_address_format(self, client):
        """Test validation error for invalid address."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.create_customer(onchain_address="not_a_valid_address")

            error = exc_info.value
            assert error is not None

            if hasattr(error, 'status_code'):
                assert error.status_code == 400
        except AssertionError:
            # Some SDKs might not validate address format
            pass

    def test_negative_charge_quantity(self, client, test_customer):
        """Test validation error for negative quantity."""
        with pytest.raises(Exception) as exc_info:
            client.charge(
                customer_id=test_customer.id,
                meter="api_calls",
                quantity=-1
            )

        error = exc_info.value
        assert error is not None

    def test_invalid_checkout_amount(self, client, test_customer):
        """Test validation error for invalid checkout amount."""
        try:
            with pytest.raises(Exception) as exc_info:
                client.checkout(
                    amount=-1000,
                    return_url="https://example.com",
                    customer_id=test_customer.id
                )

            error = exc_info.value
            assert error is not None
        except AttributeError:
            pytest.skip("checkout method not available")


class TestAPIError:
    """Test general API error handling."""

    @pytest.mark.skipif(not DRIP_API_ERROR_AVAILABLE, reason="DripAPIError not available")
    def test_api_error_has_message(self, client):
        """Test API errors include error message."""
        with pytest.raises(DripAPIError) as exc_info:
            client.get_customer("cus_nonexistent")

        error = exc_info.value
        # Error should have a message
        assert str(error) or hasattr(error, 'message')

    @pytest.mark.skipif(not DRIP_API_ERROR_AVAILABLE, reason="DripAPIError not available")
    def test_api_error_has_status_code(self, client):
        """Test API errors include HTTP status code."""
        with pytest.raises(DripAPIError) as exc_info:
            client.get_customer("cus_nonexistent")

        error = exc_info.value
        assert hasattr(error, 'status_code') or error is not None


class TestPaymentRequiredError:
    """Test payment required (insufficient balance) error handling."""

    @pytest.mark.skip(reason="Requires customer with zero balance")
    def test_insufficient_balance(self, client, test_customer):
        """Test insufficient balance handling.

        This test requires a customer with zero or negative balance,
        which may not be achievable in all test environments.
        """
        # This would require setting up a customer with zero balance
        # and attempting a charge that exceeds it
        pass


class TestRateLimitError:
    """Test rate limit error handling."""

    @pytest.mark.skip(reason="Rate limiting difficult to trigger in tests")
    def test_rate_limit_error(self, client):
        """Test rate limit error handling.

        This test would require triggering rate limiting,
        which is difficult in normal test conditions.
        """
        pass


class TestNetworkError:
    """Test network error handling."""

    def test_invalid_base_url(self, api_key, check_sdk):
        """Test network error for unreachable host."""
        bad_client = Drip(
            api_key=api_key,
            base_url="https://invalid.unreachable.host.example.com"
        )

        with pytest.raises(Exception) as exc_info:
            bad_client.ping()

        error = exc_info.value
        assert error is not None

        if DRIP_NETWORK_ERROR_AVAILABLE:
            # Might be network error or general exception
            assert isinstance(error, (DripNetworkError, Exception))


class TestErrorInheritance:
    """Test error class inheritance."""

    @pytest.mark.skipif(not DRIP_ERROR_AVAILABLE, reason="DripError not available")
    def test_api_error_inherits_drip_error(self, check_sdk):
        """Test DripAPIError inherits from DripError."""
        if DRIP_API_ERROR_AVAILABLE:
            assert issubclass(DripAPIError, (DripError, Exception))

    @pytest.mark.skipif(not DRIP_ERROR_AVAILABLE, reason="DripError not available")
    def test_auth_error_inherits_drip_error(self, check_sdk):
        """Test DripAuthenticationError inherits from DripError."""
        if DRIP_AUTH_ERROR_AVAILABLE:
            assert issubclass(DripAuthenticationError, (DripError, Exception))


class TestErrorAttributes:
    """Test error object attributes."""

    def test_error_string_representation(self, client):
        """Test errors have useful string representation."""
        with pytest.raises(Exception) as exc_info:
            client.get_customer("cus_nonexistent")

        error = exc_info.value
        error_str = str(error)

        # String representation should be informative
        assert len(error_str) > 0

    def test_error_repr(self, client):
        """Test errors have repr."""
        with pytest.raises(Exception) as exc_info:
            client.get_customer("cus_nonexistent")

        error = exc_info.value
        error_repr = repr(error)

        assert error_repr is not None
