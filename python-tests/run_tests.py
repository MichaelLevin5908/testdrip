#!/usr/bin/env python3
"""
Test runner script for Drip Python SDK tests.

This script provides convenient ways to run the test suite with
various filtering and output options.
"""

import argparse
import subprocess
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        description="Run Drip SDK Python tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run all tests
    python run_tests.py

    # Run quick smoke tests only
    python run_tests.py --quick

    # Run specific test file
    python run_tests.py --file test_async_complete.py

    # Run specific test class
    python run_tests.py --class TestAsyncCharging

    # Run with verbose output
    python run_tests.py -v

    # Generate JSON report
    python run_tests.py --json-report

    # Run only resilience tests
    python run_tests.py --marker resilience

    # Skip slow tests
    python run_tests.py --skip-slow
        """
    )

    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run only quick smoke tests"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Run specific test file"
    )
    parser.add_argument(
        "--class", "-c",
        dest="test_class",
        type=str,
        help="Run specific test class"
    )
    parser.add_argument(
        "--function", "-k",
        type=str,
        help="Run tests matching expression"
    )
    parser.add_argument(
        "--marker", "-m",
        type=str,
        help="Run tests with specific marker"
    )
    parser.add_argument(
        "--skip-slow",
        action="store_true",
        help="Skip slow tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity"
    )
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="Generate JSON report"
    )
    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML report (requires pytest-html)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage (requires pytest-cov)"
    )
    parser.add_argument(
        "--parallel", "-n",
        type=int,
        help="Run tests in parallel (requires pytest-xdist)"
    )
    parser.add_argument(
        "--failfast", "-x",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--last-failed",
        action="store_true",
        help="Run only last failed tests"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show command without running"
    )

    args = parser.parse_args()

    # Build pytest command
    cmd = ["pytest"]

    # Verbosity
    if args.verbose:
        cmd.append("-" + "v" * args.verbose)

    # Quick tests
    if args.quick:
        cmd.extend(["-m", "quick"])

    # Specific file
    if args.file:
        cmd.append(args.file)

    # Specific class
    if args.test_class:
        if args.file:
            cmd[-1] = f"{args.file}::{args.test_class}"
        else:
            cmd.extend(["-k", args.test_class])

    # Expression filter
    if args.function:
        cmd.extend(["-k", args.function])

    # Marker filter
    if args.marker:
        cmd.extend(["-m", args.marker])

    # Skip slow
    if args.skip_slow:
        if "-m" in cmd:
            idx = cmd.index("-m")
            cmd[idx + 1] = f"({cmd[idx + 1]}) and not slow"
        else:
            cmd.extend(["-m", "not slow"])

    # JSON report
    if args.json_report:
        cmd.extend(["--json-report", "--json-report-file=test_results.json"])

    # HTML report
    if args.html_report:
        cmd.extend(["--html=test_results.html", "--self-contained-html"])

    # Coverage
    if args.coverage:
        cmd.extend(["--cov=drip", "--cov-report=html", "--cov-report=term"])

    # Parallel
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    # Failfast
    if args.failfast:
        cmd.append("-x")

    # Last failed
    if args.last_failed:
        cmd.append("--lf")

    # Add default options
    cmd.extend(["--tb=short"])

    print(f"Running: {' '.join(cmd)}")

    if args.dry_run:
        return 0

    # Run pytest
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
