"""Test Drip SDK usage tracking."""

from drip import Drip

client = Drip(
    api_key="pk_live_208e2caf-be47-423a-934b-6260c8fc31c0",
    base_url="http://localhost:3001/v1",
)

CUSTOMER_ID = "seed-customer-1"

# 1. Ping the API
print("=== Ping ===")
try:
    health = client.ping()
    print(f"  OK: latency={health['latency_ms']}ms, status={health['status']}")
except Exception as e:
    print(f"  FAIL: {e}")

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
