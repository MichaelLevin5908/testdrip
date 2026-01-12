# Drip SDK Health Check CLI

A CLI tool that validates the Drip backend is functioning correctly by exercising all SDK operations.

## Purpose

- Quick verification after deployments
- Validate SDK ↔ backend contract
- Debug connectivity issues
- Pre-flight check before demos

## Installation

```bash
npm install
npm run build
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required:
- `DRIP_API_KEY` - Your Drip API key

Optional:
- `DRIP_API_URL` - Backend URL (default: http://localhost:3001)
- `TEST_CUSTOMER_ID` - Use existing customer instead of creating
- `SKIP_CLEANUP` - Keep test data after run
- `CHECK_TIMEOUT` - Per-check timeout in ms (default: 30000)

## Usage

```bash
# Run all health checks
npm run check

# Or using the CLI directly
npx drip-health check

# Run specific checks
npx drip-health check --only customer,charge

# Quick smoke test (fastest checks only)
npx drip-health check --quick

# Verbose output with details
npx drip-health check --verbose

# Output as JSON (for CI)
npx drip-health check --json

# Skip cleanup (for debugging)
npx drip-health check --no-cleanup
```

## Health Checks

| Check | Description |
|-------|-------------|
| Connectivity | Verify API is reachable |
| Authentication | Check API key validity |
| Customer Create | Create test customer |
| Customer Get | Retrieve customer by ID |
| Customer List | List customers with filter |
| Charge Create | Create charge for test customer |
| Charge Status | Check charge status |
| Balance Get | Get customer balance |
| StreamMeter Add | Test StreamMeter accumulation |
| StreamMeter Flush | Test flush and charge creation |
| Idempotency | Test duplicate detection |
| Webhook Sign | Test signature verification |
| Webhook Verify | Test invalid signature rejection |
| Run Create | Create execution run |
| Run Timeline | Verify events recorded |
| Customer Cleanup | Delete test customer |

## Example Output

```
Drip Health Check
═══════════════════════════════════════════════
   ✓ Connectivity              12ms    API reachable
   ✓ Authentication             -      API key valid
   ✓ Customer Create           89ms    cust_abc123
   ✓ Customer Get              34ms    Retrieved successfully
   ✓ Customer List             45ms    Found 1 customer
   ✓ Charge Create            156ms    chg_xyz789 ($0.01)
   ✓ Charge Status             23ms    PENDING
   ✓ Balance Get               31ms    $99.99 USDC
   ✓ StreamMeter Add           <1ms    Accumulated 100 units
   ✓ StreamMeter Flush        134ms    Charged successfully
   ✓ Idempotency              178ms    Replay detected correctly
   ✓ Webhook Sign              <1ms    Signature valid
   ✓ Webhook Verify            <1ms    Invalid sig rejected
   ✓ Run Create               201ms    run_def456
   ✓ Run Timeline              45ms    3 events recorded
   ✓ Customer Cleanup          12ms    Cleaned up
═══════════════════════════════════════════════
   15/15 checks passed                 Total: 948ms

   Status: HEALTHY ✓
```

## Exit Codes

- `0` - All checks passed
- `1` - One or more checks failed
- `2` - Configuration error

## Development

```bash
# Run in development mode
npm run dev

# Type check
npm run typecheck

# Build
npm run build
```

## License

MIT
