# Drip SDK Load Testing Tool

A CLI load testing tool that stress-tests the Drip billing backend using concurrent requests.

## Purpose

- Validate SDK performance under concurrent load
- Test idempotency behavior with parallel requests
- Find backend bottlenecks and rate limits
- Measure latency percentiles (p50, p95, p99)

## Installation

```bash
cd load-test
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
- `DEFAULT_CUSTOMER_ID` - Default customer for tests

## Usage

### Charge Burst Test

Fire N concurrent charges simultaneously:

```bash
# Run 1000 charges with 50 concurrency
npm run charge -- --concurrency 50 --total 1000 --customer <id>

# With idempotency keys
npm run charge -- -c 50 -t 1000 --customer <id> --idempotency

# Output as JSON
npm run charge -- -c 50 -t 1000 --customer <id> --output json > results.json
```

### Streaming Meter Test

Create multiple concurrent StreamMeters:

```bash
# 20 streams, each with 100 events
npm run stream -- --concurrency 20 --events 100 --customer <id>
```

### Customer Creation Test

Bulk create customers:

```bash
# Create 100 customers with 20 concurrency
npx tsx src/index.ts customers --concurrency 20 --total 100

# Test duplicate handling
npx tsx src/index.ts customers -c 20 -t 100 --test-duplicates
```

### Mixed Workload Test

Simulate realistic traffic patterns:

```bash
# 60 seconds at 100 RPS
npm run mixed -- --duration 60 --rps 100 --customer <id>

# Distribution: 70% charges, 20% balance, 10% customer ops
```

## Output Formats

### Pretty (default)

```
Drip Load Test Results
══════════════════════════════════════
Scenario:      charge-burst
Duration:      12.4s

Requests:
  Total:        1000
  Succeeded:    987 (98.7%)
  Failed:       13 (1.3%)

Latency (ms):
  Min:          45
  Max:          892
  Avg:          124
  p50:          98
  p95:          312
  p99:          654

Errors:
  RATE_LIMITED:     8
  TIMEOUT:          5

Throughput:   80.6 req/s
══════════════════════════════════════
```

### JSON

```bash
npm run charge -- -c 50 -t 1000 --output json
```

### CSV

```bash
npm run charge -- -c 50 -t 1000 --output csv
```

## Test Scenarios

| Scenario | Purpose |
|----------|---------|
| `charge` | Burst N charges simultaneously |
| `stream` | Multiple concurrent StreamMeters |
| `customers` | Bulk customer creation |
| `mixed` | Realistic mixed operations |

## Metrics Collected

- Total requests, successes, failures
- Latency: min, max, avg, p50, p95, p99
- Requests per second achieved
- Error breakdown by type (rate limit, timeout, etc.)

## Exit Codes

- `0` - All requests succeeded
- `1` - Some requests failed
- `2` - Configuration error

## Development

```bash
# Run in development mode
npm run dev -- charge -c 10 -t 100 --customer <id>

# Type check
npm run typecheck

# Build
npm run build
```

## License

MIT
