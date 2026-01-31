"""Sequential check runner matching TypeScript version."""
import time
import asyncio
from typing import List
from .types import Check, CheckContext, CheckResult
from .reporter import Reporter


async def run_check_with_timeout(
    check: Check,
    context: CheckContext,
    timeout_ms: int
) -> CheckResult:
    """Run a single check with timeout protection.

    Args:
        check: The check to run
        context: Shared check context
        timeout_ms: Timeout in milliseconds

    Returns:
        CheckResult from the check or timeout error
    """
    try:
        result = await asyncio.wait_for(
            check.run(context),
            timeout=timeout_ms / 1000.0
        )
        return result
    except asyncio.TimeoutError:
        return CheckResult(
            name=check.name,
            success=False,
            duration=timeout_ms,
            message=f"Check timed out after {timeout_ms}ms",
            suggestion="Increase timeout or check network connectivity"
        )


async def run_checks(
    checks: List[Check],
    context: CheckContext,
    reporter: Reporter
) -> List[CheckResult]:
    """Run checks sequentially, passing context between them.

    Args:
        checks: List of checks to run
        context: Shared check context
        reporter: Reporter for output

    Returns:
        List of CheckResults from all checks
    """
    results: List[CheckResult] = []

    reporter.start()

    for check in checks:
        reporter.on_check_start(check)

        start_time = time.perf_counter()
        try:
            result = await run_check_with_timeout(
                check,
                context,
                context.timeout
            )
            # Update duration with actual time if not set by timeout
            if result.duration == 0:
                result.duration = (time.perf_counter() - start_time) * 1000
        except Exception as e:
            result = CheckResult(
                name=check.name,
                success=False,
                duration=(time.perf_counter() - start_time) * 1000,
                message=f"Check failed with exception: {e}",
                suggestion="Check logs for details"
            )

        results.append(result)
        reporter.on_check_complete(result)

    reporter.finish(results)
    return results
