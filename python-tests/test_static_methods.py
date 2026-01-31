"""
Test static utility methods on Drip class.

This module tests static utility methods like generate_idempotency_key
and verify_webhook_signature.
"""

import pytest
import time
import hmac
import hashlib
import uuid
from typing import Optional

# Check if drip-sdk is available
try:
    from drip import Drip
    DRIP_SDK_AVAILABLE = True
except ImportError:
    DRIP_SDK_AVAILABLE = False
    Drip = None


pytestmark = pytest.mark.skipif(not DRIP_SDK_AVAILABLE, reason="drip-sdk not installed")


class TestGenerateIdempotencyKey:
    """Test idempotency key generation."""

    def test_deterministic_keys(self):
        """Same inputs produce same key."""
        key1 = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1
        )
        key2 = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1
        )
        assert key1 == key2

    def test_unique_keys_different_customers(self):
        """Different customers produce different keys."""
        key1 = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1
        )
        key2 = Drip.generate_idempotency_key(
            customer_id="cust_456",
            meter="tokens",
            sequence=1
        )
        assert key1 != key2

    def test_unique_keys_different_meters(self):
        """Different meters produce different keys."""
        key1 = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1
        )
        key2 = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="api_calls",
            sequence=1
        )
        assert key1 != key2

    def test_sequence_affects_key(self):
        """Different sequence numbers produce different keys."""
        key1 = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1
        )
        key2 = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=2
        )
        assert key1 != key2

    def test_optional_run_id(self):
        """Run ID included when provided."""
        key_without = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1
        )
        key_with = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1,
            run_id="run_abc"
        )
        assert key_without != key_with

    def test_key_format(self):
        """Generated key has expected format."""
        key = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=1
        )
        # Key should be a non-empty string
        assert isinstance(key, str)
        assert len(key) > 0

    def test_key_stability_across_calls(self):
        """Key is stable across multiple function calls."""
        keys = set()
        for _ in range(100):
            key = Drip.generate_idempotency_key(
                customer_id="stable_test",
                meter="tokens",
                sequence=42
            )
            keys.add(key)

        # All generated keys should be identical
        assert len(keys) == 1

    def test_key_with_special_characters(self):
        """Key generation handles special characters."""
        key = Drip.generate_idempotency_key(
            customer_id="cust_with-special.chars@test",
            meter="meter/with/slashes",
            sequence=1
        )
        assert isinstance(key, str)
        assert len(key) > 0

    def test_key_with_unicode(self):
        """Key generation handles unicode characters."""
        key = Drip.generate_idempotency_key(
            customer_id="cust_unicode_\u4e2d\u6587",
            meter="meter_\u65e5\u672c\u8a9e",
            sequence=1
        )
        assert isinstance(key, str)
        assert len(key) > 0

    def test_key_with_empty_strings(self):
        """Key generation handles empty strings."""
        key = Drip.generate_idempotency_key(
            customer_id="",
            meter="",
            sequence=0
        )
        assert isinstance(key, str)

    def test_key_with_large_sequence(self):
        """Key generation handles large sequence numbers."""
        key = Drip.generate_idempotency_key(
            customer_id="cust_123",
            meter="tokens",
            sequence=999999999999
        )
        assert isinstance(key, str)
        assert len(key) > 0

    def test_sequential_keys_are_unique(self):
        """Sequential calls with incrementing sequence produce unique keys."""
        keys = set()
        for i in range(100):
            key = Drip.generate_idempotency_key(
                customer_id="cust_123",
                meter="tokens",
                sequence=i
            )
            keys.add(key)

        # All keys should be unique
        assert len(keys) == 100


class TestVerifyWebhookSignature:
    """Test webhook signature verification."""

    def test_valid_signature_passes(self):
        """Valid webhook signature is accepted."""
        secret = "whsec_test_secret_12345"
        payload = '{"event": "charge.created", "data": {}}'
        timestamp = str(int(time.time()))

        # Generate valid signature
        signed_payload = f"{timestamp}.{payload}"
        expected_sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        signature = f"t={timestamp},v1={expected_sig}"

        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret
        )
        assert result is True

    def test_invalid_signature_fails(self):
        """Invalid webhook signature is rejected."""
        result = Drip.verify_webhook_signature(
            payload='{"event": "test"}',
            signature="t=123,v1=invalid_signature",
            secret="whsec_test"
        )
        assert result is False

    def test_expired_signature_fails(self):
        """Expired timestamp is rejected."""
        secret = "whsec_test"
        payload = '{"event": "test"}'
        old_timestamp = str(int(time.time()) - 600)  # 10 min ago

        signed_payload = f"{old_timestamp}.{payload}"
        sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        signature = f"t={old_timestamp},v1={sig}"

        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret,
            tolerance_seconds=300  # 5 min tolerance
        )
        assert result is False

    def test_signature_within_tolerance(self):
        """Signature within tolerance window is accepted."""
        secret = "whsec_test_secret"
        payload = '{"event": "test"}'
        timestamp = str(int(time.time()) - 60)  # 1 min ago

        signed_payload = f"{timestamp}.{payload}"
        sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        signature = f"t={timestamp},v1={sig}"

        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret,
            tolerance_seconds=300  # 5 min tolerance
        )
        assert result is True

    def test_malformed_signature_fails(self):
        """Malformed signature header is rejected."""
        result = Drip.verify_webhook_signature(
            payload='{"event": "test"}',
            signature="malformed_signature",
            secret="whsec_test"
        )
        assert result is False

    def test_missing_timestamp_fails(self):
        """Missing timestamp in signature is rejected."""
        result = Drip.verify_webhook_signature(
            payload='{"event": "test"}',
            signature="v1=somehash",
            secret="whsec_test"
        )
        assert result is False

    def test_missing_signature_fails(self):
        """Missing signature value is rejected."""
        result = Drip.verify_webhook_signature(
            payload='{"event": "test"}',
            signature="t=123456789",
            secret="whsec_test"
        )
        assert result is False

    def test_empty_payload(self):
        """Empty payload is handled."""
        secret = "whsec_test"
        payload = ""
        timestamp = str(int(time.time()))

        signed_payload = f"{timestamp}.{payload}"
        sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        signature = f"t={timestamp},v1={sig}"

        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret
        )
        assert result is True

    def test_json_payload_with_special_chars(self):
        """JSON payload with special characters is handled."""
        secret = "whsec_test_secret"
        payload = '{"event": "test", "message": "Hello \\"world\\" with \u4e2d\u6587"}'
        timestamp = str(int(time.time()))

        signed_payload = f"{timestamp}.{payload}"
        sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        signature = f"t={timestamp},v1={sig}"

        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret
        )
        assert result is True

    def test_multiple_signature_versions(self):
        """Multiple signature versions are handled."""
        secret = "whsec_test"
        payload = '{"event": "test"}'
        timestamp = str(int(time.time()))

        signed_payload = f"{timestamp}.{payload}"
        valid_sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        # Include multiple versions (v0 is old, v1 is current)
        signature = f"t={timestamp},v0=oldsig,v1={valid_sig}"

        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret
        )
        assert result is True

    def test_custom_tolerance(self):
        """Custom tolerance is respected."""
        secret = "whsec_test"
        payload = '{"event": "test"}'
        timestamp = str(int(time.time()) - 45)  # 45 seconds ago

        signed_payload = f"{timestamp}.{payload}"
        sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        signature = f"t={timestamp},v1={sig}"

        # Should pass with 60 second tolerance
        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret,
            tolerance_seconds=60
        )
        assert result is True

        # Should fail with 30 second tolerance
        result = Drip.verify_webhook_signature(
            payload=payload,
            signature=signature,
            secret=secret,
            tolerance_seconds=30
        )
        assert result is False


class TestParseWebhookPayload:
    """Test webhook payload parsing (if available)."""

    def test_parse_charge_created_event(self):
        """Parse charge.created event payload."""
        if not hasattr(Drip, 'parse_webhook_payload'):
            pytest.skip("parse_webhook_payload not available")

        payload = '''{
            "event": "charge.created",
            "data": {
                "id": "ch_123",
                "amount": 100,
                "currency": "USD"
            }
        }'''

        result = Drip.parse_webhook_payload(payload)
        assert result is not None
        assert result.event == "charge.created"

    def test_parse_charge_settled_event(self):
        """Parse charge.settled event payload."""
        if not hasattr(Drip, 'parse_webhook_payload'):
            pytest.skip("parse_webhook_payload not available")

        payload = '''{
            "event": "charge.settled",
            "data": {
                "id": "ch_456",
                "amount": 200,
                "settled_at": "2024-01-15T10:00:00Z"
            }
        }'''

        result = Drip.parse_webhook_payload(payload)
        assert result is not None
        assert result.event == "charge.settled"


class TestFormatters:
    """Test utility formatting methods (if available)."""

    def test_format_currency(self):
        """Format currency values."""
        if not hasattr(Drip, 'format_currency'):
            pytest.skip("format_currency not available")

        result = Drip.format_currency(1000, "USD")
        assert "$10.00" in result or "10.00" in result

    def test_format_quantity(self):
        """Format quantity values."""
        if not hasattr(Drip, 'format_quantity'):
            pytest.skip("format_quantity not available")

        result = Drip.format_quantity(1000000, "tokens")
        assert "1M" in result or "1,000,000" in result


class TestVersionInfo:
    """Test version and SDK info methods."""

    def test_sdk_version(self):
        """SDK exposes version info."""
        if hasattr(Drip, 'version'):
            version = Drip.version
            assert version is not None
            assert isinstance(version, str)
        elif hasattr(Drip, '__version__'):
            version = Drip.__version__
            assert version is not None

    def test_sdk_name(self):
        """SDK exposes name info."""
        if hasattr(Drip, 'sdk_name'):
            name = Drip.sdk_name
            assert name is not None
            assert "drip" in name.lower()


class TestClientFactory:
    """Test client factory methods (if available)."""

    def test_from_env(self, api_key, base_url):
        """Create client from environment variables."""
        import os
        os.environ["DRIP_API_KEY"] = api_key
        os.environ["DRIP_API_URL"] = base_url

        if hasattr(Drip, 'from_env'):
            client = Drip.from_env()
            assert client is not None
            client.close()

    def test_from_config(self, api_key, base_url):
        """Create client from config dict."""
        if hasattr(Drip, 'from_config'):
            config = {
                "api_key": api_key,
                "base_url": base_url
            }
            client = Drip.from_config(config)
            assert client is not None
            client.close()
