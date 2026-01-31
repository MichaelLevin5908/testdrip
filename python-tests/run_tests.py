#!/usr/bin/env python3
"""Run Drip SDK Python tests with various options.

This CLI tool provides convenient ways to run the Drip SDK test suite
with different configurations and output formats.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --only health      # Run only health tests
    python run_tests.py --verbose          # Run with verbose output
    python run_tests.py --quick            # Run quick smoke tests only
    python run_tests.py --json             # Output results as JSON
"""
import argparse
import subprocess
import sys
import os


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run Drip SDK Python tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_tests.py                         Run all tests
    python run_tests.py --only health customers Run specific test files
    python run_tests.py -v                      Verbose output
    python run_tests.py --quick                 Quick smoke tests only
    python run_tests.py --json                  JSON output for CI
    python run_tests.py --parallel              Run tests in parallel
    python run_tests.py --coverage              Run with coverage report
        """
    )

    parser.add_argument(
        "--only",
        nargs="+",
        metavar="TEST",
        help="Run only specific test modules (e.g., health customers charging)"
    )

    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="TEST",
        help="Exclude specific test modules"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test output"
    )

    parser.add_argument(
        "-vv", "--very-verbose",
        action="store_true",
        help="Very verbose test output (shows all output)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only quick smoke tests (marked with @pytest.mark.quick)"
    )

    parser.add_argument(
        "--slow",
        action="store_true",
        help="Include slow-running tests"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (requires pytest-json-report)"
    )

    parser.add_argument(
        "--json-file",
        metavar="FILE",
        default="results.json",
        help="JSON output file path (default: results.json)"
    )

    parser.add_argument(
        "--parallel", "-n",
        type=int,
        metavar="NUM",
        help="Run tests in parallel with NUM workers (requires pytest-xdist)"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report (requires pytest-cov)"
    )

    parser.add_argument(
        "-k", "--keyword",
        metavar="EXPR",
        help="Only run tests matching the given expression"
    )

    parser.add_argument(
        "-x", "--exitfirst",
        action="store_true",
        help="Exit on first failure"
    )

    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Drop into debugger on failure"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command that would be run without executing"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available test modules"
    )

    args = parser.parse_args()

    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Handle --list option
    if args.list:
        list_test_modules(script_dir)
        return 0

    # Build pytest command
    cmd = ["pytest"]

    # Determine which tests to run
    if args.only:
        # Run specific test files
        test_files = []
        for test_name in args.only:
            if not test_name.startswith("test_"):
                test_name = f"test_{test_name}"
            if not test_name.endswith(".py"):
                test_name = f"{test_name}.py"
            test_path = os.path.join(script_dir, test_name)
            if os.path.exists(test_path):
                test_files.append(test_path)
            else:
                print(f"Warning: Test file not found: {test_name}")
        if not test_files:
            print("Error: No valid test files specified")
            return 1
        cmd.extend(test_files)
    else:
        # Run all tests in the directory
        cmd.append(script_dir)

    # Exclude tests
    if args.exclude:
        for test_name in args.exclude:
            if not test_name.startswith("test_"):
                test_name = f"test_{test_name}"
            cmd.extend(["--ignore", os.path.join(script_dir, f"{test_name}.py")])

    # Verbosity
    if args.very_verbose:
        cmd.append("-vv")
    elif args.verbose:
        cmd.append("-v")

    # Quick tests only
    if args.quick:
        cmd.extend(["-m", "quick"])

    # Include slow tests
    if args.slow:
        # Don't filter by marker - run all including slow
        pass

    # JSON output
    if args.json:
        cmd.extend([
            "--json-report",
            f"--json-report-file={args.json_file}"
        ])

    # Parallel execution
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    # Coverage
    if args.coverage:
        cmd.extend([
            "--cov=drip",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_html"
        ])

    # Keyword filter
    if args.keyword:
        cmd.extend(["-k", args.keyword])

    # Exit on first failure
    if args.exitfirst:
        cmd.append("-x")

    # Debug on failure
    if args.pdb:
        cmd.append("--pdb")

    # Print command if dry run
    if args.dry_run:
        print("Would run:")
        print(" ".join(cmd))
        return 0

    # Print what we're running
    print(f"Running: {' '.join(cmd)}")
    print()

    # Execute pytest
    return subprocess.call(cmd)


def list_test_modules(script_dir):
    """List all available test modules."""
    print("Available test modules:")
    print()

    test_files = sorted([
        f for f in os.listdir(script_dir)
        if f.startswith("test_") and f.endswith(".py")
    ])

    descriptions = {
        "test_health.py": "Health checks and connectivity tests",
        "test_customers.py": "Customer CRUD operations",
        "test_charging.py": "Charge creation and retrieval",
        "test_streaming.py": "StreamMeter high-frequency metering",
        "test_meters.py": "Meter listing operations",
        "test_checkout.py": "Fiat on-ramp checkout",
        "test_webhooks.py": "Webhook CRUD and signature verification",
        "test_workflows.py": "Workflow and run tracking",
        "test_async.py": "AsyncDrip client operations",
        "test_idempotency.py": "Idempotency key handling",
        "test_errors.py": "Error handling and exceptions",
        "test_cost_estimation.py": "Cost estimation features",
    }

    for test_file in test_files:
        name = test_file.replace("test_", "").replace(".py", "")
        desc = descriptions.get(test_file, "")
        print(f"  {name:20} {desc}")

    print()
    print("Usage: python run_tests.py --only <module> [<module> ...]")
    print("Example: python run_tests.py --only health customers")


if __name__ == "__main__":
    sys.exit(main())
