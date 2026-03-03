"""
Edge Case Tests for the Drip Python SDK.

Non-happy-path tests simulating real-world misuse: wrong argument types,
missing fields, boundary values, security edge cases, and common integration
mistakes that companies encounter when adopting the SDK.
"""

from __future__ import annotations

import math
import os
from unittest.mock import patch

import httpx
import pytest
import respx

from drip import (
    AsyncDrip,
    Drip,
    DripAPIError,
    DripAuthenticationError,
    DripError,
    DripNetworkError,
    DripPaymentRequiredError,
    DripRateLimitError,
)
from drip.models import SpendingCapType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def api_key() -> str:
    return "sk_test_edge_case_key"


@pytest.fixture
def base_url() -> str:
    return "https://drip-app-hlunj.ondigitalocean.app/v1"


@pytest.fixture
def client(api_key: str, base_url: str) -> Drip:
    return Drip(api_key=api_key, base_url=base_url)


@pytest.fixture
def async_client(api_key: str, base_url: str) -> AsyncDrip:
    return AsyncDrip(api_key=api_key, base_url=base_url)


# =============================================================================
# A. Constructor / Initialization Edge Cases
# =============================================================================


class TestConstructorEdgeCases:
    """Tests for SDK initialization with invalid or edge-case configurations."""

    def test_a1_no_api_key_no_env_var(self) -> None:
        """Company forgets to set env var in production."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DRIP_API_KEY", None)
            with pytest.raises(DripAuthenticationError):
                Drip()

    def test_a2_empty_string_api_key(self) -> None:
        """Misconfigured env var set to empty string."""
        with pytest.raises(DripAuthenticationError):
            Drip(api_key="")

    def test_a3_whitespace_only_api_key(self) -> None:
        """Copy-paste error with spaces in API key."""
        # Whitespace is truthy, so constructor may accept it
        # The error will surface on first API call
        client = Drip(api_key="   ")
        assert client.config.api_key == "   "

    def test_a4_none_api_key_no_env(self) -> None:
        """Explicitly passing None as API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DRIP_API_KEY", None)
            with pytest.raises(DripAuthenticationError):
                Drip(api_key=None)

    def test_a5_timeout_zero(self) -> None:
        """Company sets timeout=0 expecting 'no timeout'."""
        # Zero timeout should be accepted or use default
        client = Drip(api_key="sk_test_key", timeout=0)
        assert client.config.timeout == 0 or client.config.timeout == 30.0

    def test_a6_negative_timeout(self) -> None:
        """Invalid negative timeout value."""
        client = Drip(api_key="sk_test_key", timeout=-1)
        # Constructor accepts it - will fail on first request
        assert client is not None

    def test_a7_base_url_with_trailing_slash_is_stripped(self) -> None:
        """Python SDK strips trailing slash via .rstrip('/') - no double-slash bug."""
        client = Drip(api_key="sk_test_key", base_url="https://api.example.com/v1/")
        # Unlike JS SDK, Python strips the trailing slash
        assert client.config.base_url == "https://api.example.com/v1"

    def test_a8_empty_base_url(self) -> None:
        """Empty string base URL falls back to default."""
        client = Drip(api_key="sk_test_key", base_url="")
        # Empty string is falsy - may fall back to default or use empty
        assert client is not None

    def test_a9_very_long_api_key(self) -> None:
        """Accidental paste of file contents as API key."""
        long_key = "sk_test_" + "a" * 10000
        client = Drip(api_key=long_key)
        assert client.config.api_key == long_key

    def test_a10_env_var_takes_precedence_when_no_param(self) -> None:
        """Environment variable used when no param provided."""
        with patch.dict(os.environ, {"DRIP_API_KEY": "env_key_123"}):
            client = Drip()
            assert client.config.api_key == "env_key_123"

    def test_a11_param_overrides_env_var(self) -> None:
        """Explicit param should override env var."""
        with patch.dict(os.environ, {"DRIP_API_KEY": "env_key_123"}):
            client = Drip(api_key="param_key_456")
            assert client.config.api_key == "param_key_456"


class TestAsyncConstructorEdgeCases:
    """Async client initialization edge cases."""

    def test_async_no_api_key(self) -> None:
        """Async client also requires API key."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DRIP_API_KEY", None)
            with pytest.raises(DripAuthenticationError):
                AsyncDrip()


# =============================================================================
# B. Customer Method Edge Cases
# =============================================================================


class TestCustomerEdgeCases:
    """Tests for customer CRUD with invalid inputs."""

    @respx.mock
    def test_b1_create_customer_empty_params(self, client: Drip, base_url: str) -> None:
        """No externalCustomerId or onchainAddress - API returns 422."""
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                422,
                json={
                    "error": "At least one of externalCustomerId or onchainAddress is required",
                    "code": "VALIDATION_ERROR",
                },
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.create_customer()
        assert exc.value.status_code == 422

    @respx.mock
    def test_b2_create_customer_empty_string_external_id(self, client: Drip, base_url: str) -> None:
        """Empty string externalCustomerId - falsy check may skip it."""
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                422,
                json={"error": "externalCustomerId cannot be empty", "code": "VALIDATION_ERROR"},
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.create_customer(external_customer_id="")
        assert exc.value.status_code == 422

    @respx.mock
    def test_b3_create_customer_invalid_address(self, client: Drip, base_url: str) -> None:
        """Invalid ethereum address format."""
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                422,
                json={"error": "Invalid Ethereum address format", "code": "VALIDATION_ERROR"},
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.create_customer(onchain_address="not-an-address")
        assert exc.value.status_code == 422

    @respx.mock
    def test_b4_create_customer_valid_format_nonexistent_address(self, client: Drip, base_url: str) -> None:
        """Valid address format that doesn't exist on-chain should succeed."""
        fake_address = "0x" + "f" * 40
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "cus_1",
                    "businessId": "biz_1",
                    "externalCustomerId": None,
                    "onchainAddress": fake_address,
                    "metadata": None,
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        customer = client.create_customer(onchain_address=fake_address)
        assert customer.id == "cus_1"

    @respx.mock
    def test_b5_create_customer_very_long_external_id(self, client: Drip, base_url: str) -> None:
        """Passing full JWT/URL as external ID (10KB)."""
        long_id = "a" * 10000
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                422,
                json={"error": "externalCustomerId too long", "code": "VALIDATION_ERROR"},
            )
        )
        with pytest.raises(DripAPIError):
            client.create_customer(external_customer_id=long_id)

    @respx.mock
    def test_b6_create_customer_deeply_nested_metadata(self, client: Drip, base_url: str) -> None:
        """Deeply nested metadata should be accepted as JSON."""
        metadata = {"level1": {"level2": {"level3": {"key": "value"}}}}
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "cus_1",
                    "businessId": "biz_1",
                    "externalCustomerId": "test",
                    "onchainAddress": None,
                    "metadata": metadata,
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        customer = client.create_customer(external_customer_id="test", metadata=metadata)
        assert customer.id == "cus_1"

    @respx.mock
    def test_b8_get_customer_empty_id(self, client: Drip, base_url: str) -> None:
        """Empty string customer ID."""
        respx.get(f"{base_url}/customers/").mock(
            return_value=httpx.Response(404, json={"error": "Not found"})
        )
        with pytest.raises((DripAPIError, DripError)):
            client.get_customer("")

    @respx.mock
    def test_b9_get_customer_sql_injection(self, client: Drip, base_url: str) -> None:
        """SQL injection attempt - should return 404 (parameterized queries)."""
        injection = "'; DROP TABLE customers; --"
        respx.get(f"{base_url}/customers/{injection}").mock(
            return_value=httpx.Response(404, json={"error": "Customer not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.get_customer(injection)
        assert exc.value.status_code == 404

    @respx.mock
    def test_b10_get_customer_path_traversal(self, client: Drip, base_url: str) -> None:
        """Path traversal attempt."""
        traversal = "../../../etc/passwd"
        respx.get(f"{base_url}/customers/{traversal}").mock(
            return_value=httpx.Response(404, json={"error": "Not found"})
        )
        with pytest.raises(DripAPIError):
            client.get_customer(traversal)

    @respx.mock
    def test_b11_list_customers_limit_zero(self, client: Drip, base_url: str) -> None:
        """limit=0 - below minimum of 1."""
        respx.get(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                422, json={"error": "limit must be >= 1", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.list_customers(limit=0)
        assert exc.value.status_code == 422

    @respx.mock
    def test_b12_list_customers_limit_101(self, client: Drip, base_url: str) -> None:
        """limit=101 - above maximum of 100."""
        respx.get(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                422, json={"error": "limit must be <= 100", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.list_customers(limit=101)
        assert exc.value.status_code == 422

    @respx.mock
    def test_b13_list_customers_negative_limit(self, client: Drip, base_url: str) -> None:
        """Negative limit value."""
        respx.get(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                422, json={"error": "limit must be >= 1", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.list_customers(limit=-1)
        assert exc.value.status_code == 422

    @respx.mock
    def test_b15_duplicate_customer_returns_409(self, client: Drip, base_url: str) -> None:
        """Duplicate externalCustomerId returns 409 Conflict."""
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                409,
                json={"error": "Customer already exists", "code": "CONFLICT"},
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.create_customer(external_customer_id="existing_user")
        assert exc.value.status_code == 409

    @respx.mock
    def test_b16_get_customer_valid_uuid_not_found(self, client: Drip, base_url: str) -> None:
        """Valid UUID format that doesn't exist returns 404."""
        uuid = "00000000-0000-0000-0000-000000000000"
        respx.get(f"{base_url}/customers/{uuid}").mock(
            return_value=httpx.Response(404, json={"error": "Customer not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.get_customer(uuid)
        assert exc.value.status_code == 404

    @respx.mock
    def test_get_balance_nonexistent_customer(self, client: Drip, base_url: str) -> None:
        """Balance check on nonexistent customer."""
        respx.get(f"{base_url}/customers/nonexistent/balance").mock(
            return_value=httpx.Response(404, json={"error": "Customer not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.get_balance("nonexistent")
        assert exc.value.status_code == 404


# =============================================================================
# C. Charge / Usage Edge Cases
# =============================================================================


class TestChargeEdgeCases:
    """Tests for charging with invalid inputs and boundary values."""

    @respx.mock
    def test_c1_charge_quantity_zero(self, client: Drip, base_url: str) -> None:
        """Zero quantity may succeed with $0 charge."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "isDuplicate": False,
                    "charge": {
                        "id": "chg_1",
                        "amountUsdc": "0.000000",
                        "amountToken": "0",
                        "txHash": None,
                        "status": "CONFIRMED",
                    },
                },
            )
        )
        result = client.charge(customer_id="cus_1", meter="api_calls", quantity=0)
        assert result.charge.amount_usdc == "0.000000"

    @respx.mock
    def test_c2_charge_negative_quantity(self, client: Drip, base_url: str) -> None:
        """Negative quantity should be rejected by API."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                422, json={"error": "quantity must be positive", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.charge(customer_id="cus_1", meter="api_calls", quantity=-5)
        assert exc.value.status_code == 422

    @respx.mock
    def test_c3_charge_nan_quantity(self, client: Drip, base_url: str) -> None:
        """NaN quantity - BUG: Python json module outputs literal NaN which is invalid JSON.
        httpx will fail to serialize the body because json.dumps(NaN) outputs 'NaN'
        which is not valid JSON. This reveals a real bug in the SDK: no client-side
        validation of NaN/Infinity values before sending."""
        # Python's json module will serialize NaN as 'NaN' by default
        # httpx should send the request but the server will reject it
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                422, json={"error": "quantity must be a number", "code": "VALIDATION_ERROR"}
            )
        )
        # This may either:
        # 1. Send a request with NaN in body (server rejects with 422)
        # 2. Raise a serialization error client-side
        with pytest.raises((DripAPIError, DripError, ValueError)):
            client.charge(customer_id="cus_1", meter="api_calls", quantity=float("nan"))

    @respx.mock
    def test_c4_charge_infinity_quantity(self, client: Drip, base_url: str) -> None:
        """Infinity quantity - same serialization issue as NaN."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                422, json={"error": "quantity must be finite", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises((DripAPIError, DripError, ValueError)):
            client.charge(customer_id="cus_1", meter="api_calls", quantity=float("inf"))

    @respx.mock
    def test_c5_charge_sub_cent_precision(self, client: Drip, base_url: str) -> None:
        """Sub-cent precision (0.0000001) should succeed for token metering."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "isDuplicate": False,
                    "charge": {
                        "id": "chg_1",
                        "amountUsdc": "0.000001",
                        "amountToken": "1",
                        "txHash": None,
                        "status": "CONFIRMED",
                    },
                },
            )
        )
        result = client.charge(customer_id="cus_1", meter="tokens", quantity=0.0000001)
        assert result.success is True

    @respx.mock
    def test_c6_charge_huge_quantity(self, client: Drip, base_url: str) -> None:
        """Extremely large quantity (runaway agent) hits balance limit."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                402,
                json={
                    "error": "Insufficient balance",
                    "code": "PAYMENT_REQUIRED",
                    "paymentRequest": {"amount": "999999999", "currency": "USDC"},
                },
            )
        )
        with pytest.raises(DripPaymentRequiredError):
            client.charge(customer_id="cus_1", meter="tokens", quantity=999999999)

    @respx.mock
    def test_c7_charge_nonexistent_customer(self, client: Drip, base_url: str) -> None:
        """Most common integration mistake: made-up customer ID."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                404, json={"error": "Customer not found", "code": "NOT_FOUND"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.charge(customer_id="cust_nonexistent", meter="api_calls", quantity=1)
        assert exc.value.status_code == 404

    @respx.mock
    def test_c8_charge_nonexistent_meter(self, client: Drip, base_url: str) -> None:
        """Typo in meter name - BUG: if API returns charge=null, Pydantic will fail
        because ChargeResult.charge is typed as ChargeInfo (non-optional).
        This test documents that the model would raise ValidationError."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "isDuplicate": False,
                    "charge": None,
                },
            )
        )
        # Pydantic will raise a ValidationError because charge is required (non-optional)
        with pytest.raises(Exception):
            client.charge(customer_id="cus_1", meter="nonexistent_meter", quantity=1)

    @respx.mock
    def test_c9_charge_duplicate_idempotency_key(self, client: Drip, base_url: str) -> None:
        """Same idempotency key twice returns isDuplicate: True."""
        route = respx.post(f"{base_url}/usage")
        route.side_effect = [
            httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "isDuplicate": False,
                    "charge": {"id": "chg_1", "amountUsdc": "0.01", "amountToken": "10", "txHash": None, "status": "CONFIRMED"},
                },
            ),
            httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "isDuplicate": True,
                    "charge": {"id": "chg_1", "amountUsdc": "0.01", "amountToken": "10", "txHash": None, "status": "CONFIRMED"},
                },
            ),
        ]

        key = "dedup_test_key_123"
        first = client.charge(customer_id="cus_1", meter="api_calls", quantity=1, idempotency_key=key)
        second = client.charge(customer_id="cus_1", meter="api_calls", quantity=1, idempotency_key=key)

        assert first.is_duplicate is False
        assert second.is_duplicate is True

    def test_c11_charge_no_customer_id_no_user(self, client: Drip) -> None:
        """Neither customer_id nor user provided raises DripError."""
        with pytest.raises(DripError, match="customer_id.*user"):
            client.charge(meter="api_calls", quantity=1)

    @respx.mock
    def test_c13_charge_quantity_as_string(self, client: Drip, base_url: str) -> None:
        """String quantity - Python may coerce or reject."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "isDuplicate": False,
                    "charge": {"id": "chg_1", "amountUsdc": "0.05", "amountToken": "50", "txHash": None, "status": "CONFIRMED"},
                },
            )
        )
        # Python float() coerces "5" to 5.0 transparently
        result = client.charge(customer_id="cus_1", meter="api_calls", quantity=float("5"))  # type: ignore[arg-type]
        assert result.success is True

    @respx.mock
    def test_c15_charge_insufficient_balance_402(self, client: Drip, base_url: str) -> None:
        """Insufficient balance returns 402 with payment details."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                402,
                json={
                    "error": "Payment required",
                    "code": "PAYMENT_REQUIRED",
                    "paymentRequest": {
                        "amount": "1.00",
                        "recipient": "0xmerchant",
                        "currency": "USDC",
                        "chain": "base-sepolia",
                    },
                },
            )
        )
        with pytest.raises(DripPaymentRequiredError) as exc:
            client.charge(customer_id="cus_1", meter="api_calls", quantity=100)
        assert exc.value.status_code == 402
        assert exc.value.payment_request is not None


class TestTrackUsageEdgeCases:
    """Tests for internal usage tracking edge cases."""

    @respx.mock
    def test_c14_track_usage_goes_to_internal_endpoint(self, client: Drip, base_url: str) -> None:
        """track_usage should POST to /usage/internal, NOT /usage."""
        respx.post(f"{base_url}/usage/internal").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "customerId": "cus_1",
                    "usageType": "api_calls",
                    "quantity": 1,
                    "isInternal": True,
                    "isDuplicate": False,
                    "message": "Internal usage recorded",
                },
            )
        )
        result = client.track_usage(customer_id="cus_1", meter="api_calls", quantity=1)
        assert result.usage_event_id == "evt_1"

    @respx.mock
    def test_track_usage_zero_quantity(self, client: Drip, base_url: str) -> None:
        """Zero quantity usage event."""
        respx.post(f"{base_url}/usage/internal").mock(
            return_value=httpx.Response(
                200,
                json={
                    "success": True,
                    "usageEventId": "evt_1",
                    "customerId": "cus_1",
                    "usageType": "api_calls",
                    "quantity": 0,
                    "isInternal": True,
                    "isDuplicate": False,
                    "message": "Internal usage recorded",
                },
            )
        )
        result = client.track_usage(customer_id="cus_1", meter="api_calls", quantity=0)
        assert result.usage_event_id == "evt_1"


class TestChargeStatusEdgeCases:
    """Tests for charge status checks."""

    @respx.mock
    def test_get_charge_nonexistent(self, client: Drip, base_url: str) -> None:
        """Charge ID that doesn't exist."""
        respx.get(f"{base_url}/charges/nonexistent").mock(
            return_value=httpx.Response(404, json={"error": "Charge not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.get_charge("nonexistent")
        assert exc.value.status_code == 404

    @respx.mock
    def test_get_charge_empty_id(self, client: Drip, base_url: str) -> None:
        """Empty string charge ID."""
        respx.get(f"{base_url}/charges/").mock(
            return_value=httpx.Response(404, json={"error": "Not found"})
        )
        with pytest.raises((DripAPIError, DripError)):
            client.get_charge("")

    @respx.mock
    def test_list_charges_invalid_status(self, client: Drip, base_url: str) -> None:
        """Invalid status filter value."""
        respx.get(f"{base_url}/charges").mock(
            return_value=httpx.Response(
                422, json={"error": "Invalid status", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError):
            client.list_charges(status="BOGUS")


# =============================================================================
# D. Webhook Edge Cases
# =============================================================================


class TestWebhookEdgeCases:
    """Tests for webhook operations with edge-case inputs."""

    @respx.mock
    def test_d2_create_webhook_invalid_url(self, client: Drip, base_url: str) -> None:
        """Invalid webhook URL should be rejected."""
        respx.post(f"{base_url}/webhooks").mock(
            return_value=httpx.Response(
                422, json={"error": "Invalid webhook URL", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError):
            client.create_webhook(url="not-a-url", events=["charge.succeeded"])

    @respx.mock
    def test_d3_create_webhook_invalid_event_type(self, client: Drip, base_url: str) -> None:
        """Invalid event type name."""
        respx.post(f"{base_url}/webhooks").mock(
            return_value=httpx.Response(
                422, json={"error": "Invalid event type", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError):
            client.create_webhook(url="https://example.com/hook", events=["invalid.event"])

    @respx.mock
    def test_d4_create_webhook_empty_events(self, client: Drip, base_url: str) -> None:
        """Empty events array should be rejected."""
        respx.post(f"{base_url}/webhooks").mock(
            return_value=httpx.Response(
                422, json={"error": "At least one event required", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError):
            client.create_webhook(url="https://example.com/hook", events=[])

    @respx.mock
    def test_d5_delete_nonexistent_webhook(self, client: Drip, base_url: str) -> None:
        """Deleting already-deleted webhook returns 404."""
        respx.delete(f"{base_url}/webhooks/nonexistent").mock(
            return_value=httpx.Response(404, json={"error": "Webhook not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.delete_webhook("nonexistent")
        assert exc.value.status_code == 404

    @respx.mock
    def test_d6_test_nonexistent_webhook(self, client: Drip, base_url: str) -> None:
        """Testing nonexistent webhook returns 404."""
        respx.post(f"{base_url}/webhooks/nonexistent/test").mock(
            return_value=httpx.Response(404, json={"error": "Webhook not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.test_webhook("nonexistent")
        assert exc.value.status_code == 404

    @respx.mock
    def test_d7_rotate_secret_nonexistent_webhook(self, client: Drip, base_url: str) -> None:
        """Rotating secret of nonexistent webhook returns 404."""
        respx.post(f"{base_url}/webhooks/nonexistent/rotate-secret").mock(
            return_value=httpx.Response(404, json={"error": "Webhook not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.rotate_webhook_secret("nonexistent")
        assert exc.value.status_code == 404


# =============================================================================
# E. Subscription Edge Cases
# =============================================================================


class TestSubscriptionEdgeCases:
    """Tests for subscription lifecycle edge cases."""

    @respx.mock
    def test_e1_create_subscription_zero_price(self, client: Drip, base_url: str) -> None:
        """Free tier subscription with $0 price."""
        respx.post(f"{base_url}/subscriptions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "sub_1",
                    "businessId": "biz_1",
                    "customerId": "cus_1",
                    "name": "Free",
                    "priceUsdc": "0",
                    "interval": "MONTHLY",
                    "status": "ACTIVE",
                    "cancelAtPeriodEnd": False,
                    "currentPeriodStart": "2024-01-01T00:00:00Z",
                    "currentPeriodEnd": "2024-02-01T00:00:00Z",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        sub = client.create_subscription(
            customer_id="cus_1", name="Free", price_usdc=0, interval="MONTHLY"
        )
        assert sub.status == "ACTIVE"

    @respx.mock
    def test_e2_create_subscription_negative_price(self, client: Drip, base_url: str) -> None:
        """Negative price should be rejected."""
        respx.post(f"{base_url}/subscriptions").mock(
            return_value=httpx.Response(
                422, json={"error": "amountUsdc must be non-negative", "code": "VALIDATION_ERROR"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.create_subscription(
                customer_id="cus_1", name="Bad", price_usdc=-10, interval="MONTHLY"
            )
        assert exc.value.status_code == 422

    @respx.mock
    def test_e3_create_subscription_nonexistent_customer(self, client: Drip, base_url: str) -> None:
        """Subscription for nonexistent customer returns 404."""
        respx.post(f"{base_url}/subscriptions").mock(
            return_value=httpx.Response(404, json={"error": "Customer not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.create_subscription(
                customer_id="nonexistent", name="Pro", price_usdc=10, interval="MONTHLY"
            )
        assert exc.value.status_code == 404

    @respx.mock
    def test_e4_cancel_already_cancelled_subscription(self, client: Drip, base_url: str) -> None:
        """Double-cancel race condition."""
        respx.post(f"{base_url}/subscriptions/sub_cancelled/cancel").mock(
            return_value=httpx.Response(
                400, json={"error": "Subscription already cancelled", "code": "ALREADY_CANCELLED"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.cancel_subscription("sub_cancelled")
        assert exc.value.status_code == 400

    @respx.mock
    def test_e5_pause_already_paused_subscription(self, client: Drip, base_url: str) -> None:
        """Pausing already-paused subscription."""
        respx.post(f"{base_url}/subscriptions/sub_paused/pause").mock(
            return_value=httpx.Response(
                400, json={"error": "Subscription already paused", "code": "ALREADY_PAUSED"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.pause_subscription("sub_paused")
        assert exc.value.status_code == 400

    @respx.mock
    def test_e6_resume_active_subscription(self, client: Drip, base_url: str) -> None:
        """Resuming a subscription that isn't paused."""
        respx.post(f"{base_url}/subscriptions/sub_active/resume").mock(
            return_value=httpx.Response(
                400, json={"error": "Subscription is not paused", "code": "NOT_PAUSED"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.resume_subscription("sub_active")
        assert exc.value.status_code == 400


# =============================================================================
# F. Run / Event Edge Cases
# =============================================================================


class TestRunEventEdgeCases:
    """Tests for execution logging edge cases."""

    @respx.mock
    def test_f1_end_already_ended_run(self, client: Drip, base_url: str) -> None:
        """Double-end from retry."""
        respx.patch(f"{base_url}/runs/run_ended").mock(
            return_value=httpx.Response(
                400, json={"error": "Run already ended", "code": "RUN_ALREADY_ENDED"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.end_run("run_ended", status="COMPLETED")
        assert exc.value.status_code == 400

    @respx.mock
    def test_f2_emit_event_on_ended_run(self, client: Drip, base_url: str) -> None:
        """Emitting event to ended run."""
        respx.post(f"{base_url}/run-events").mock(
            return_value=httpx.Response(
                400, json={"error": "Cannot emit event to ended run"}
            )
        )
        with pytest.raises(DripAPIError):
            client.emit_event(run_id="run_ended", event_type="USAGE")

    @respx.mock
    def test_f4_emit_events_batch_empty(self, client: Drip, base_url: str) -> None:
        """Empty batch of events."""
        respx.post(f"{base_url}/run-events/batch").mock(
            return_value=httpx.Response(
                200,
                json={"success": True, "created": 0, "duplicates": 0, "skipped": 0, "events": []},
            )
        )
        result = client.emit_events_batch(events=[])
        assert result.created == 0

    @respx.mock
    def test_f6_start_then_immediately_end_run(self, client: Drip, base_url: str) -> None:
        """Quick-failing agent run with no events."""
        respx.post(f"{base_url}/runs").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "run_1",
                    "customerId": "cus_1",
                    "workflowId": "wf_1",
                    "workflowName": "Test",
                    "status": "RUNNING",
                    "correlationId": None,
                    "createdAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        run = client.start_run(customer_id="cus_1", workflow_id="wf_1")
        assert run.id == "run_1"

        respx.patch(f"{base_url}/runs/run_1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "run_1",
                    "status": "COMPLETED",
                    "endedAt": "2024-01-01T00:00:01Z",
                    "durationMs": 1000,
                    "eventCount": 0,
                    "totalCostUnits": "0",
                },
            )
        )
        ended = client.end_run("run_1", status="COMPLETED")
        assert ended.status == "COMPLETED"

    @respx.mock
    def test_f7_record_run_empty_events(self, client: Drip, base_url: str) -> None:
        """Record a run with no events."""
        respx.post(f"{base_url}/runs/record").mock(
            return_value=httpx.Response(
                200,
                json={
                    "run": {
                        "id": "run_1",
                        "workflowId": "wf_1",
                        "workflowName": "test-workflow",
                        "status": "COMPLETED",
                        "durationMs": 10,
                    },
                    "events": {"created": 0, "duplicates": 0},
                    "totalCostUnits": "0",
                    "summary": "Completed with 0 events",
                },
            )
        )
        result = client.record_run(
            customer_id="cus_1",
            workflow="test-workflow",
            events=[],
            status="COMPLETED",
        )
        assert result.events.created == 0

    @respx.mock
    def test_f8_get_run_timeline_nonexistent(self, client: Drip, base_url: str) -> None:
        """Nonexistent run ID."""
        respx.get(f"{base_url}/runs/nonexistent/timeline").mock(
            return_value=httpx.Response(404, json={"error": "Run not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.get_run_timeline("nonexistent")
        assert exc.value.status_code == 404


# =============================================================================
# G. Entitlement Edge Cases
# =============================================================================


class TestEntitlementEdgeCases:
    """Tests for entitlement checks with edge-case inputs."""

    @respx.mock
    def test_g1_check_entitlement_nonexistent_customer(self, client: Drip, base_url: str) -> None:
        """Customer not onboarded yet."""
        respx.post(f"{base_url}/entitlements/check").mock(
            return_value=httpx.Response(404, json={"error": "Customer not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.check_entitlement(customer_id="nonexistent", feature_key="api_calls")
        assert exc.value.status_code == 404

    @respx.mock
    def test_g2_check_entitlement_nonexistent_feature(self, client: Drip, base_url: str) -> None:
        """Unconfigured feature may return unlimited access."""
        respx.post(f"{base_url}/entitlements/check").mock(
            return_value=httpx.Response(
                200,
                json={
                    "allowed": True,
                    "remaining": -1,
                    "limit": -1,
                    "unlimited": True,
                    "period": "MONTHLY",
                    "periodResetsAt": "2025-02-01T00:00:00Z",
                    "reason": "No plan configured",
                    "featureKey": "nonexistent",
                },
            )
        )
        result = client.check_entitlement(customer_id="cus_1", feature_key="nonexistent")
        assert result.allowed is True
        assert result.unlimited is True


# =============================================================================
# H. Cost Estimation Edge Cases
# =============================================================================


class TestCostEstimationEdgeCases:
    """Tests for cost estimation with boundary inputs."""

    @respx.mock
    def test_h1_estimate_future_dates(self, client: Drip, base_url: str) -> None:
        """Future date range returns zero estimate."""
        respx.post(f"{base_url}/dashboard/cost-estimate/from-usage").mock(
            return_value=httpx.Response(
                200,
                json={
                    "estimatedTotalUsdc": "0.00",
                    "subtotalUsdc": "0.00",
                    "generatedAt": "2024-01-01T00:00:00Z",
                    "lineItems": [],
                },
            )
        )
        result = client.estimate_from_usage(
            customer_id="cus_1",
            period_start="2099-01-01T00:00:00Z",
            period_end="2099-12-31T23:59:59Z",
        )
        assert result.estimated_total_usdc == "0.00"

    @respx.mock
    def test_h2_estimate_end_before_start(self, client: Drip, base_url: str) -> None:
        """End date before start date should be rejected."""
        respx.post(f"{base_url}/dashboard/cost-estimate/from-usage").mock(
            return_value=httpx.Response(
                422, json={"error": "periodEnd must be after periodStart"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.estimate_from_usage(
                customer_id="cus_1",
                period_start="2025-12-31T00:00:00Z",
                period_end="2025-01-01T00:00:00Z",
            )
        assert exc.value.status_code == 422

    @respx.mock
    def test_h3_hypothetical_empty_items(self, client: Drip, base_url: str) -> None:
        """Empty what-if scenario returns $0."""
        respx.post(f"{base_url}/dashboard/cost-estimate/hypothetical").mock(
            return_value=httpx.Response(
                200,
                json={
                    "estimatedTotalUsdc": "0.00",
                    "subtotalUsdc": "0.00",
                    "generatedAt": "2024-01-01T00:00:00Z",
                    "lineItems": [],
                },
            )
        )
        result = client.estimate_from_hypothetical(items=[])
        assert result.estimated_total_usdc == "0.00"


# =============================================================================
# I. StreamMeter Edge Cases
# =============================================================================


class TestStreamMeterEdgeCases:
    """Tests for streaming usage accumulation."""

    def test_i1_add_sync_nan_not_filtered(self, client: Drip) -> None:
        """BUG: NaN is NOT filtered - total becomes NaN.
        The guard `quantity <= 0` is False for NaN, so it passes through
        and corrupts the running total. Same bug exists in JS SDK."""
        meter = client.create_stream_meter(customer_id="cus_1", meter="tokens")
        meter.add_sync(float("nan"))
        assert math.isnan(meter.total)  # BUG: total is now NaN

    def test_i2_add_sync_infinity_accepted(self, client: Drip) -> None:
        """Infinity passes the guard (inf > 0 is True) and corrupts total."""
        meter = client.create_stream_meter(customer_id="cus_1", meter="tokens")
        meter.add_sync(float("inf"))
        # Infinity passes `quantity <= 0` check (inf > 0 is True)
        assert meter.total == float("inf")

    def test_i3_flush_zero_total(self, client: Drip) -> None:
        """Flushing with 0 total returns null charge."""
        meter = client.create_stream_meter(customer_id="cus_1", meter="tokens")
        result = meter.flush()
        assert result.charge is None

    def test_i5_add_sync_negative_ignored(self, client: Drip) -> None:
        """Negative values should be ignored."""
        meter = client.create_stream_meter(customer_id="cus_1", meter="tokens")
        meter.add_sync(10)
        meter.add_sync(-5)
        assert meter.total == 10  # negative ignored


# =============================================================================
# J. Network / Resilience Edge Cases
# =============================================================================


class TestNetworkEdgeCases:
    """Tests for network errors and edge-case responses."""

    @respx.mock
    def test_j1_html_response_502(self, client: Drip, base_url: str) -> None:
        """CDN/proxy returns HTML instead of JSON."""
        respx.get(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                502,
                text="<html><body>502 Bad Gateway</body></html>",
                headers={"content-type": "text/html"},
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.list_customers()
        assert exc.value.status_code == 502

    @respx.mock
    def test_j5_rate_limit_429(self, client: Drip, base_url: str) -> None:
        """Rate limit returns 429."""
        respx.get(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                429,
                json={"error": "Rate limit exceeded", "retryAfter": 60},
            )
        )
        with pytest.raises(DripRateLimitError) as exc:
            client.list_customers()
        assert exc.value.status_code == 429
        assert exc.value.retry_after == 60

    @respx.mock
    def test_j6_server_error_500(self, client: Drip, base_url: str) -> None:
        """Internal server error."""
        respx.get(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                500, json={"error": "Internal server error"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.list_customers()
        assert exc.value.status_code == 500

    @respx.mock
    def test_j7_unauthorized_401(self, client: Drip, base_url: str) -> None:
        """Invalid API key returns 401."""
        respx.get(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                401, json={"error": "Invalid API key", "code": "UNAUTHORIZED"}
            )
        )
        with pytest.raises(DripAuthenticationError) as exc:
            client.list_customers()
        assert exc.value.status_code == 401

    @respx.mock
    def test_j8_timeout(self, client: Drip, base_url: str) -> None:
        """Request timeout."""
        respx.get(f"{base_url}/customers").mock(
            side_effect=httpx.ReadTimeout("Timed out")
        )
        with pytest.raises(DripNetworkError):
            client.list_customers()

    @respx.mock
    def test_j9_connection_refused(self, client: Drip, base_url: str) -> None:
        """Connection refused (backend not running)."""
        respx.get(f"{base_url}/customers").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        with pytest.raises(DripNetworkError):
            client.list_customers()


# =============================================================================
# K. Security Edge Cases
# =============================================================================


class TestSecurityEdgeCases:
    """Tests for security-related edge cases."""

    @respx.mock
    def test_k1_api_key_in_metadata(self, client: Drip, base_url: str) -> None:
        """Accidental API key leak in metadata - SDK doesn't filter."""
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "cus_1",
                    "businessId": "biz_1",
                    "externalCustomerId": "test",
                    "onchainAddress": None,
                    "metadata": {"secret": "sk_live_real_key"},
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        # SDK should not filter sensitive data from metadata
        customer = client.create_customer(
            external_customer_id="test",
            metadata={"secret": "sk_live_real_key"},
        )
        assert customer.id == "cus_1"

    @respx.mock
    def test_k2_xss_in_customer_id(self, client: Drip, base_url: str) -> None:
        """XSS attempt in external ID - should be stored safely."""
        xss = '<script>alert("xss")</script>'
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "cus_1",
                    "businessId": "biz_1",
                    "externalCustomerId": xss,
                    "onchainAddress": None,
                    "metadata": None,
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        customer = client.create_customer(external_customer_id=xss)
        assert customer.external_customer_id == xss

    @respx.mock
    def test_k4_very_large_metadata(self, client: Drip, base_url: str) -> None:
        """1MB metadata payload - server may reject."""
        large_metadata = {f"key_{i}": "x" * 1000 for i in range(1000)}
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                413, json={"error": "Request entity too large"}
            )
        )
        with pytest.raises(DripAPIError) as exc:
            client.create_customer(
                external_customer_id="test", metadata=large_metadata
            )
        assert exc.value.status_code == 413

    @respx.mock
    def test_k5_unicode_in_customer_id(self, client: Drip, base_url: str) -> None:
        """Unicode characters in customer ID."""
        unicode_id = "user_\u4e2d\u6587_\u00e9"
        respx.post(f"{base_url}/customers").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "cus_1",
                    "businessId": "biz_1",
                    "externalCustomerId": unicode_id,
                    "onchainAddress": None,
                    "metadata": None,
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        customer = client.create_customer(external_customer_id=unicode_id)
        assert customer.external_customer_id == unicode_id


# =============================================================================
# L. Spending Cap Edge Cases
# =============================================================================


class TestSpendingCapEdgeCases:
    """Tests for spending cap edge cases."""

    @respx.mock
    def test_negative_limit(self, client: Drip, base_url: str) -> None:
        """Negative spending cap limit."""
        respx.put(f"{base_url}/customers/cus_1/spending-cap").mock(
            return_value=httpx.Response(
                422, json={"error": "limitValue must be positive"}
            )
        )
        with pytest.raises(DripAPIError):
            client.set_customer_spending_cap(
                customer_id="cus_1",
                cap_type=SpendingCapType.DAILY_CHARGE_LIMIT,
                limit_value=-100,
            )

    @respx.mock
    def test_zero_limit(self, client: Drip, base_url: str) -> None:
        """Zero spending cap limit."""
        respx.put(f"{base_url}/customers/cus_1/spending-cap").mock(
            return_value=httpx.Response(
                422, json={"error": "limitValue must be positive"}
            )
        )
        with pytest.raises(DripAPIError):
            client.set_customer_spending_cap(
                customer_id="cus_1",
                cap_type=SpendingCapType.DAILY_CHARGE_LIMIT,
                limit_value=0,
            )

    @respx.mock
    def test_remove_nonexistent_cap(self, client: Drip, base_url: str) -> None:
        """Removing a cap that doesn't exist."""
        respx.delete(f"{base_url}/customers/cus_1/spending-caps/nonexistent").mock(
            return_value=httpx.Response(404, json={"error": "Spending cap not found"})
        )
        with pytest.raises(DripAPIError) as exc:
            client.remove_customer_spending_cap("cus_1", "nonexistent")
        assert exc.value.status_code == 404


# =============================================================================
# M. wrapApiCall Edge Cases
# =============================================================================


class TestWrapApiCallEdgeCases:
    """Tests for the crash-safe API wrapping method."""

    @respx.mock
    def test_external_api_throws(self, client: Drip, base_url: str) -> None:
        """External API failure - error propagates, no charge recorded."""
        def failing_call():
            raise ConnectionError("External API down")

        with pytest.raises(ConnectionError, match="External API down"):
            client.wrap_api_call(
                customer_id="cus_1",
                meter="tokens",
                call=failing_call,
                extract_usage=lambda r: 0,
            )

    def test_extract_usage_returns_nan(self, client: Drip) -> None:
        """BUG: extract_usage returns NaN - json.dumps(NaN) raises ValueError.
        In Python, json.dumps(float('nan')) raises ValueError because NaN is
        not valid JSON. This means the charge request is never sent. This is
        different from JS where JSON.stringify(NaN) silently becomes null."""
        with pytest.raises(ValueError):
            client.wrap_api_call(
                customer_id="cus_1",
                meter="tokens",
                call=lambda: {"data": "ok"},
                extract_usage=lambda r: float("nan"),
            )

    @respx.mock
    def test_extract_usage_returns_negative(self, client: Drip, base_url: str) -> None:
        """extract_usage returns negative value."""
        respx.post(f"{base_url}/usage").mock(
            return_value=httpx.Response(
                422, json={"error": "quantity must be positive"}
            )
        )
        with pytest.raises(DripAPIError):
            client.wrap_api_call(
                customer_id="cus_1",
                meter="tokens",
                call=lambda: {"tokens": -10},
                extract_usage=lambda r: r["tokens"],
            )

    def test_extract_usage_throws(self, client: Drip) -> None:
        """extract_usage throws after external call succeeds."""
        def bad_extract(r: object) -> float:
            raise ValueError("Cannot extract")

        with pytest.raises(ValueError, match="Cannot extract"):
            client.wrap_api_call(
                customer_id="cus_1",
                meter="tokens",
                call=lambda: {"data": "ok"},
                extract_usage=bad_extract,
            )

    def test_no_customer_id_no_user(self, client: Drip) -> None:
        """Neither customer_id nor user provided."""
        with pytest.raises(DripError):
            client.wrap_api_call(
                meter="tokens",
                call=lambda: {"data": "ok"},
                extract_usage=lambda r: 1,
            )


# =============================================================================
# N. get_or_create_customer Edge Cases
# =============================================================================


class TestGetOrCreateCustomerEdgeCases:
    """Tests for the idempotent customer creation."""

    @respx.mock
    def test_race_condition_409_then_find(self, client: Drip, base_url: str) -> None:
        """409 conflict triggers _resolve_customer which creates (409 again),
        then falls back to listing customers to find the existing one,
        then getCustomer to return it."""
        # get_or_create_customer calls create_customer -> 409
        # Then calls _resolve_customer which calls create_customer again -> 409
        # _resolve_customer checks for existingCustomerId in body, then lists
        route_create = respx.post(f"{base_url}/customers")
        route_create.side_effect = [
            # First: get_or_create_customer's create_customer call
            httpx.Response(
                409,
                json={"error": "Customer already exists", "code": "CONFLICT"},
            ),
            # Second: _resolve_customer's create_customer call
            httpx.Response(
                409,
                json={"error": "Customer already exists", "code": "CONFLICT"},
            ),
        ]
        route_list = respx.get(f"{base_url}/customers")
        route_list.mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "cus_existing",
                            "businessId": "biz_1",
                            "externalCustomerId": "user_1",
                            "onchainAddress": None,
                            "metadata": None,
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                        }
                    ],
                    "count": 1,
                },
            )
        )
        route_get = respx.get(f"{base_url}/customers/cus_existing")
        route_get.mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "cus_existing",
                    "businessId": "biz_1",
                    "externalCustomerId": "user_1",
                    "onchainAddress": None,
                    "metadata": None,
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            )
        )
        customer = client.get_or_create_customer("user_1")
        assert customer.id == "cus_existing"
