"""Test Drip SDK usage tracking."""

import os
from dotenv import load_dotenv
load_dotenv()

from drip import Drip

API_KEY = os.getenv('DRIP_API_KEY')
if not API_KEY:
    print("Error: DRIP_API_KEY environment variable not set")
    exit(1)

DRIP_API_URL = os.getenv('DRIP_API_URL', 'https://drip-app-hlunj.ondigitalocean.app')
BASE_URL = f"{DRIP_API_URL}/v1" if not DRIP_API_URL.endswith('/v1') else DRIP_API_URL

client = Drip(
    api_key=API_KEY,
    base_url=BASE_URL,
)

CUSTOMER_ID = os.getenv('TEST_CUSTOMER_ID')

# 1. Ping the API
print("=== Ping ===")
try:
    health = client.ping()
    print(f"  OK: latency={health['latency_ms']}ms, status={health['status']}")
except Exception as e:
    print(f"  FAIL: {e}")

# 1b. Create a customer if none provided
if not CUSTOMER_ID:
    import secrets
    print("\n=== Create Customer ===")
    try:
        random_address = "0x" + secrets.token_hex(20)
        customer = client.create_customer(
            onchain_address=random_address,
            external_customer_id=f"usage_test_{secrets.token_hex(4)}",
            metadata={"test": "usage_tracking"},
        )
        CUSTOMER_ID = customer.id
        print(f"  OK: created {CUSTOMER_ID}")
    except Exception as e:
        print(f"  FAIL: {e}")
        exit(1)

# 2. Track usage (no billing) - 1500 tokens — no idempotency_key needed, SDK auto-generates
print("\n=== Track Usage: 1500 tokens ===")
try:
    result = client.track_usage(
        customer_id=CUSTOMER_ID,
        meter="tokens",
        quantity=1500,
    )
    print(f"  OK: {result}")
except Exception as e:
    print(f"  FAIL: {e}")

# 3. Track more usage with metadata — no idempotency_key needed
print("\n=== Track Usage: 1 api_call with metadata ===")
try:
    result = client.track_usage(
        customer_id=CUSTOMER_ID,
        meter="api_calls",
        quantity=1,
        description="test API call from Python SDK",
        metadata={"source": "testdrip", "model": "gpt-4"},
    )
    print(f"  OK: {result}")
except Exception as e:
    print(f"  FAIL: {e}")

# 4. Get customer details
print("\n=== Get Customer ===")
try:
    customer = client.get_customer(customer_id=CUSTOMER_ID)
    print(f"  OK: id={customer.id}, status={customer.status}, external_id={customer.external_customer_id}")
except Exception as e:
    print(f"  FAIL: {e}")

# 5. Check balance
print("\n=== Get Balance ===")
try:
    balance = client.get_balance(customer_id=CUSTOMER_ID)
    print(f"  OK: balance={balance.balance_usdc} USDC, available={balance.available_usdc} USDC")
except Exception as e:
    print(f"  FAIL: {e}")

# 6. List charges
print("\n=== List Charges ===")
try:
    charges = client.list_charges()
    print(f"  OK: {charges.count} charges found")
    for c in charges.data[:3]:
        print(f"    - {c.id}: {c.amount_usdc} USDC")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nAll tests complete!")
