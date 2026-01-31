#!/usr/bin/env python3
"""Drip SDK Health Check CLI - Python version."""
import asyncio
import sys
import click
from dotenv import load_dotenv

from .config import load_config
from .runner import run_checks
from .reporter import Reporter
from .types import CheckContext
from .checks import all_checks, quick_checks, get_checks_by_name

# Load environment variables from .env file
load_dotenv()


@click.command()
@click.option('--only', help='Run only specified checks (comma-separated)')
@click.option('--quick', is_flag=True, help='Run quick checks only')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.option('--json', 'json_output', is_flag=True, help='Output as JSON')
@click.option('--env', 'environment', help='Target environment')
@click.option('--no-cleanup', is_flag=True, help='Skip cleanup after tests')
def main(only, quick, verbose, json_output, environment, no_cleanup):
    """
    Drip SDK Health Check CLI

    Validates SDK operations against a live Drip backend.

    \b
    Examples:
        python -m python.cli                    # Run all checks
        python -m python.cli --quick            # Run quick checks only
        python -m python.cli --only customer,charge
        python -m python.cli --json             # CI-friendly output
    """
    try:
        config = load_config(environment)
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(2)

    # Determine which checks to run
    if quick:
        checks = quick_checks
    elif only:
        checks = get_checks_by_name(only.split(','))
        if not checks:
            available = [c.name for c in all_checks]
            click.echo(f"No matching checks found. Available: {available}", err=True)
            sys.exit(2)
    else:
        checks = all_checks

    # Create context
    context = CheckContext(
        api_key=config.api_key,
        api_url=config.api_url,
        test_customer_id=config.test_customer_id,
        skip_cleanup=no_cleanup or config.skip_cleanup,
        timeout=config.timeout
    )

    # Create reporter
    reporter = Reporter(verbose=verbose, json_output=json_output)

    # Run checks
    results = asyncio.run(run_checks(checks, context, reporter))

    # Exit with appropriate code
    failures = sum(1 for r in results if not r.success)
    sys.exit(1 if failures > 0 else 0)


if __name__ == '__main__':
    main()
